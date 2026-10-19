"""Basic text reading with Tesseract, for when the AI reader can't be reached.

Tesseract runs on this server with no outside connection. Pictures go to it
through stdin and text comes back through stdout, so nothing is written to disk.

OCR gives plain text and can't tell which part is the brand or the bottler. So
unlike the AI reader, this reader looks on the label for what the application
says. It can only find or not find text that is really printed; it can't invent
any. OCR misreads small print and drops accents, and it can't see bold type, so
results from this reader are never marked Fail (see soften_for_ocr).
"""

import os
import re
import shutil
import subprocess
from difflib import SequenceMatcher

from app.reading.schema import BoldLook, FieldReading, LabelReading, Readability, WarningReading
from app.rules.application import Application
from app.rules.countries import find_countries
from app.rules.names import LEAD_IN
from app.rules.net_contents import AMOUNT
from app.rules.warning import GOVERNMENT_WARNING

TESSERACT = "tesseract"
CLEAR_SIMILARITY = 0.98  # this close to the application counts as read clearly
FOUND_SIMILARITY = 0.80  # this close counts as found, but hard to read

ALCOHOL_LINE = re.compile(r"\d\s*%|\bproof\b", re.IGNORECASE)
ALCOHOL_WORDS = re.compile(r"\balc|\bvol|\bproof\b|\balcohol\b", re.IGNORECASE)
HEADING = re.compile(r"government\s+warning", re.IGNORECASE)
ORIGIN_WORDS = re.compile(r"\b(?:product|produce)\s+of\b|\bmade\s+in\b", re.IGNORECASE)
WARNING_END = "health problems."


class OcrFailed(Exception):
    """Tesseract is missing or could not read a picture."""


def tesseract_available() -> bool:
    return shutil.which(TESSERACT) is not None


def ocr_text(jpeg: bytes, timeout: float = 60) -> str:
    try:
        result = subprocess.run(
            [TESSERACT, "stdin", "stdout", "-l", "eng", "--psm", "3"],
            input=jpeg,
            capture_output=True,
            timeout=timeout,
            env={**os.environ, "OMP_THREAD_LIMIT": "1"},
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise OcrFailed(str(error)) from error
    if result.returncode != 0:
        raise OcrFailed(f"tesseract exited with {result.returncode}")
    return result.stdout.decode("utf-8", errors="replace")


def found(text: str | None, image_number: int | None, clear: bool) -> FieldReading:
    if text is None:
        return FieldReading(
            text=None, readability=Readability.NOT_FOUND, image_number=None, english_meaning=None
        )
    readability = Readability.CLEAR if clear else Readability.UNCLEAR
    return FieldReading(
        text=text, readability=readability, image_number=image_number, english_meaning=None
    )


def without_other_fields(pages: list[str]) -> list[str]:
    """The pages minus lines that belong to other fields: the bottler or importer line,
    the country of origin line, and the warning. Otherwise a brand could be "found" in
    the importer's company name when the label's own brand line can't be read."""
    kept = []
    for page in pages:
        lines = []
        for line in page.splitlines():
            if HEADING.search(line):
                break  # the warning runs to the end of its block
            if not (LEAD_IN.match(line) or ORIGIN_WORDS.search(line)):
                lines.append(line)
        kept.append("\n".join(lines))
    return kept


def find_phrase(said: str, pages: list[str]) -> FieldReading:
    """The stretch of label text most like `said`, compared word by word."""
    target = " ".join(said.split()).casefold()
    size = len(target.split())
    if not size:
        return found(None, None, False)
    best: tuple[float, str, int] | None = None
    for number, page in enumerate(pages, start=1):
        words = page.split()
        for length in {max(1, size - 1), size, size + 1}:
            for start in range(len(words) - length + 1):
                window = " ".join(words[start : start + length])
                score = SequenceMatcher(None, target, window.casefold()).ratio()
                if best is None or score > best[0]:
                    best = (score, window, number)
    if best is None or best[0] < FOUND_SIMILARITY:
        return found(None, None, False)
    score, window, number = best
    return found(window, number, score >= CLEAR_SIMILARITY)


def lines_matching(pages: list[str], test) -> list[tuple[str, int]]:
    return [
        (line.strip(), number)
        for number, page in enumerate(pages, start=1)
        for line in page.splitlines()
        if line.strip() and test(line)
    ]


def one_line(candidates: list[tuple[str, int]]) -> FieldReading:
    """The first candidate line. If the label has several different ones, OCR can't
    tell which is the real statement, so the field is marked hard to read."""
    if not candidates:
        return found(None, None, False)
    text, number = candidates[0]
    different = {c.casefold() for c, _ in candidates}
    return found(text, number, clear=len(different) == 1)


def find_warning(pages: list[str]) -> WarningReading:
    for number, page in enumerate(pages, start=1):
        joined = " ".join(page.split())
        match = HEADING.search(joined)
        if not match:
            continue
        rest = joined[match.start() :]
        end = rest.casefold().find(WARNING_END)
        if end >= 0:
            text = rest[: end + len(WARNING_END)]
        else:
            text = rest[: len(GOVERNMENT_WARNING) + 40]
        field = found(text, number, clear=True)
        return WarningReading(
            **field.model_dump(), heading_bold=BoldLook.CANT_TELL, rest_bold=BoldLook.CANT_TELL
        )
    return WarningReading(
        **found(None, None, False).model_dump(),
        heading_bold=BoldLook.CANT_TELL,
        rest_bold=BoldLook.CANT_TELL,
    )


def ocr_reading(images: list[bytes], application: Application) -> LabelReading:
    """Read the label's pictures with Tesseract and pick out each field."""
    pages = [ocr_text(image) for image in images]

    alcohol = lines_matching(
        pages, lambda line: ALCOHOL_LINE.search(line) and ALCOHOL_WORDS.search(line)
    )
    if not alcohol:
        alcohol = lines_matching(pages, ALCOHOL_LINE.search)
    bottler = lines_matching(pages, LEAD_IN.match)
    # "Product of ..." lines first. Otherwise, for an import, any line naming a country
    # that isn't the bottler's address (which may name a state such as Georgia).
    country = lines_matching(pages, ORIGIN_WORDS.search)
    if not country and application.country_of_origin:
        country = lines_matching(
            pages, lambda line: bool(find_countries(line)) and not LEAD_IN.match(line)
        )

    return LabelReading(
        brand_name=find_phrase(application.brand_name, without_other_fields(pages)),
        class_type=find_phrase(application.class_type, without_other_fields(pages)),
        alcohol_content=one_line(alcohol),
        net_contents=one_line(lines_matching(pages, AMOUNT.search)),
        bottler_name_address=one_line(bottler)
        if bottler
        else find_phrase(application.bottler_name_address, pages),
        country_of_origin=one_line(country),
        government_warning=find_warning(pages),
        image_problems=[],
    )
