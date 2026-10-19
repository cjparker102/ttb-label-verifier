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

from app.intake.images import UnreadableFile, shrink_to_jpeg, split_pages
from app.reading.claude import ReadingFailed, ReadResult
from app.reading.ocr import OcrFailed, ocr_reading, tesseract_available
from app.reading.schema import LabelReading
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


async def check_one(
    application: Application,
    images: list[tuple[str, bytes]],
    reader: LabelReader | None,
    max_edge: int,
    ocr_fallback: bool = True,
) -> CheckOutcome:
    """Check one product's label images, given as (file name, bytes), against its
    application. Uses the AI reader, or basic text reading when there is no AI reader
    or it fails, if `ocr_fallback` allows."""
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
            return CheckOutcome(
                result=check_label(application, read.reading),
                reading=read.reading,
                images=prepared,
                seconds=time.perf_counter() - start,
                reading_seconds=read.seconds,
                input_tokens=read.input_tokens,
                output_tokens=read.output_tokens,
            )

    if not (ocr_fallback and tesseract_available()):
        raise NoReader
    reading_start = time.perf_counter()
    try:
        reading = await asyncio.to_thread(ocr_reading, prepared, application)
    except OcrFailed as error:
        log.warning("Basic text reading failed: %s", type(error).__name__)
        raise NoReader from error
    return CheckOutcome(
        result=soften_for_ocr(check_label(application, reading)),
        reading=reading,
        images=prepared,
        seconds=time.perf_counter() - start,
        reading_seconds=time.perf_counter() - reading_start,
        read_by="ocr",
    )
