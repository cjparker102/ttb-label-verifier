"""Checks one label: prepare the images, read them, and apply the rules."""

import asyncio
import dataclasses
import logging
import time
import traceback
from dataclasses import dataclass
from typing import Protocol

import anthropic
from PIL import Image, UnidentifiedImageError

from app.highlights import Highlight, all_words, find_highlights, ocr_passes
from app.intake.images import UnreadableFile, shrink_to_jpeg, split_pages
from app.photo_coach import low_resolution
from app.reading.claude import ReadingFailed, ReadResult
from app.reading.ocr import OcrFailed, ocr_reading, tesseract_available
from app.reading.schema import LabelReading
from app.reading.strokes import HeadingWeight, heading_weight
from app.reading.words import Passes
from app.rules.application import Application
from app.rules.results import Status
from app.rules.verdict import LabelResult, check_label

log = logging.getLogger("ttb_label_verifier")

OCR_CAUTION = "Basic text reading can't be sure about this, so please check it by eye. "


class LabelReader(Protocol):
    async def read(self, images: list[bytes]) -> ReadResult: ...


class NotAnImage(ValueError):
    """An uploaded file could not be opened as an image."""

    def __init__(self, name: str):
        super().__init__(f'"{name}" is not an image this app can read.')
        self.name = name


MAX_PICTURES_PER_LABEL = 8  # after PDF and TIFF pages are counted

# What can go wrong opening a file that claims to be a picture, including "picture
# bombs" that claim billions of pixels.
CANNOT_OPEN = (UnreadableFile, UnidentifiedImageError, OSError, Image.DecompressionBombError)


class TooManyPictures(ValueError):
    """A label with more pictures than the reader is given at once."""

    def __init__(self, count: int):
        super().__init__(
            f"This label has {count} pictures once PDF and TIFF pages are counted. "
            f"The limit is {MAX_PICTURES_PER_LABEL}."
        )


class NoReader(Exception):
    """Neither the AI reader nor basic text reading could read the label."""


@dataclass(frozen=True)
class CheckOutcome:
    result: LabelResult
    reading: LabelReading
    images: list[bytes]  # the shrunken JPEGs, kept only to show in the response
    seconds: float  # from receiving the images to the finished result
    reading_seconds: float
    read_by: str = "ai"  # "ai", or "ocr" for basic text reading
    input_tokens: int = 0  # what the AI reader used, for cost estimates
    output_tokens: int = 0
    photo_problems: tuple[str, ...] = ()  # for the photo tips; never affects results
    highlights: tuple[Highlight, ...] = ()  # where fields to look at are; never affects results
    second_reading: bool = False  # whether Tesseract's words were ready for the rules


def soften_for_ocr(result: LabelResult) -> LabelResult:
    """Basic text reading misreads small print, drops accents, and can't see bold.
    So nothing it finds is called a Problem: every Fail becomes Needs review. And a
    match that passed only by overlooking capitals, punctuation, or spacing needs
    review too, because OCR can't tell those apart from a lost accent."""

    def soften(check):
        if check.status == Status.FAIL:
            return dataclasses.replace(
                check, status=Status.REVIEW, reason=OCR_CAUTION + check.reason
            )
        if check.status == Status.PASS and check.note:
            return dataclasses.replace(
                check,
                status=Status.REVIEW,
                reason=OCR_CAUTION + "It can't see accents reliably. " + check.reason,
                note=None,
            )
        return check

    fields = [
        dataclasses.replace(field, checks=tuple(soften(c) for c in field.checks))
        for field in result.fields
    ]
    return LabelResult(tuple(fields))


# Tesseract's words are a second reading of the label, for the outlines and for some
# rules. They are optional, so no failure while finding them ever stops a check, and a
# finished check waits only this long for them. Speed matters more.
OUTLINE_WAIT = 1.0  # seconds


async def find_words(pictures: list[bytes]) -> Passes | None:
    """Words and where they are on each picture, or None if Tesseract fails."""
    try:
        return await asyncio.to_thread(ocr_passes, pictures)
    except Exception as error:
        log.warning("Finding words for outlines failed: %s", type(error).__name__)
        return None


async def second_reading(words: asyncio.Task | None) -> Passes | None:
    """Tesseract's words, if they are ready in time."""
    if words is None:
        return None
    try:
        return await asyncio.wait_for(asyncio.shield(words), OUTLINE_WAIT)
    except TimeoutError:
        log.warning("Outlines skipped: finding the words took too long")
        return None


async def warning_picture(pictures: list[bytes], reading: LabelReading) -> Passes | None:
    """Tesseract's words on the picture the AI reader found the warning on, and no words
    for the others. None if there is no warning or Tesseract fails."""
    number = reading.government_warning.image_number
    if number is None or not 0 < number <= len(pictures):
        return None
    found = await find_words([pictures[number - 1]])
    if found is None:
        return None
    return [found[0] if i == number - 1 else [] for i in range(len(pictures))]


async def measure_heading(
    pictures: list[bytes], reading: LabelReading, passes: Passes | None
) -> HeadingWeight | None:
    """The warning heading's strokes against the words after it, on the picture the AI
    reader found the warning on, from Tesseract's words. None if they can't be measured,
    and no failure here ever stops a check."""
    number = reading.government_warning.image_number
    if passes is None or number is None or not 0 < number <= len(pictures):
        return None
    try:
        return await asyncio.to_thread(heading_weight, pictures[number - 1], passes[number - 1])
    except Exception as error:
        log.warning("Measuring the warning heading failed: %s", type(error).__name__)
        return None


def outlines(passes: Passes | None, result: LabelResult) -> tuple[Highlight, ...]:
    if passes is None:
        return ()
    try:
        return tuple(find_highlights(result, [all_words(p) for p in passes]))
    except Exception as error:
        log.warning("Outlining fields failed: %s", type(error).__name__)
        return ()


async def check_one(
    application: Application,
    images: list[tuple[str, bytes]],
    reader: LabelReader | None,
    max_edge: int,
    ocr_fallback: bool = True,
    outline: bool = False,
    warning_only: bool = False,
) -> CheckOutcome:
    """Check one product's label images, given as (file name, bytes), against its
    application. Uses the AI reader, or basic text reading when there is no AI reader
    or it fails, if `ocr_fallback` allows. With `outline`, Tesseract also reads the
    pictures while the AI reader works: a second reading, used by some rules and to find
    where each field to look at is on the pictures. With `warning_only`, as in batches,
    Tesseract reads only the picture with the warning, after the AI reader, so the
    warning gets its second reading at less cost."""
    start = time.perf_counter()
    pictures = []
    for name, data in images:
        try:
            # Image work is slow Python code, so it runs off the event loop.
            pictures += await asyncio.to_thread(split_pages, name, data)
        except CANNOT_OPEN as error:
            raise NotAnImage(name) from error
    if len(pictures) > MAX_PICTURES_PER_LABEL:
        raise TooManyPictures(len(pictures))
    prepared = []
    for name, data in pictures:
        try:
            prepared.append(await asyncio.to_thread(shrink_to_jpeg, data, max_edge))
        except CANNOT_OPEN as error:
            raise NotAnImage(name) from error

    # Shrinking never enlarges a picture, so the shrunken copies show if any was small.
    small = await asyncio.to_thread(low_resolution, prepared)

    # Tesseract looks for the words while the AI reader works, so it rarely adds time.
    words = asyncio.create_task(find_words(prepared)) if outline and tesseract_available() else None
    try:
        return await read_and_decide(
            application, prepared, reader, ocr_fallback, small, words, start, warning_only
        )
    finally:
        if words is not None:
            words.cancel()  # only matters if the check failed before using them


async def read_and_decide(
    application: Application,
    prepared: list[bytes],
    reader: LabelReader | None,
    ocr_fallback: bool,
    small: bool,
    words: asyncio.Task | None,
    start: float,
    warning_only: bool = False,
) -> CheckOutcome:
    """The rest of check_one: read the pictures, apply the rules, add the outlines."""
    if reader is not None:
        try:
            read = await reader.read(prepared)
        except Exception as error:  # any failure of the AI reader falls back to basic reading
            log.warning(
                "Label reading failed: %s status=%s request_id=%s",
                type(error).__name__,
                getattr(error, "status_code", None),
                getattr(error, "request_id", None),
            )
            if not isinstance(error, ReadingFailed | anthropic.APIError):
                # Where it failed, without the error message, which could quote label text.
                log.warning(
                    "Unexpected failure at:\n%s", "".join(traceback.format_tb(error.__traceback__))
                )
            if not ocr_fallback:
                raise NoReader from error
        else:
            problems = [str(problem) for problem in read.reading.image_problems]
            if small:
                problems.append("low_resolution")
            passes = await second_reading(words)
            if passes is None and warning_only and tesseract_available():
                passes = await warning_picture(prepared, read.reading)
            heading = await measure_heading(prepared, read.reading, passes)
            result = check_label(application, read.reading, passes, heading)
            return CheckOutcome(
                result=result,
                reading=read.reading,
                images=prepared,
                seconds=time.perf_counter() - start,
                reading_seconds=read.seconds,
                input_tokens=read.input_tokens,
                output_tokens=read.output_tokens,
                photo_problems=tuple(problems),
                highlights=outlines(passes, result),
                second_reading=passes is not None,
            )

    if not (ocr_fallback and tesseract_available()):
        raise NoReader
    reading_start = time.perf_counter()
    try:
        reading = await asyncio.to_thread(ocr_reading, prepared, application)
    except OcrFailed as error:
        log.warning("Basic text reading failed: %s", type(error).__name__)
        raise NoReader from error
    reading_seconds = time.perf_counter() - reading_start
    result = soften_for_ocr(check_label(application, reading))
    highlights = outlines(await second_reading(words), result)
    return CheckOutcome(
        result=result,
        reading=reading,
        images=prepared,
        seconds=time.perf_counter() - start,
        reading_seconds=reading_seconds,
        read_by="ocr",
        photo_problems=("low_resolution",) if small else (),
        highlights=highlights,
    )
