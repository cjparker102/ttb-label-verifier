"""Checks one label: prepare the images, read them, and apply the rules."""

import asyncio
import time
from dataclasses import dataclass
from typing import Protocol

from PIL import UnidentifiedImageError

from app.intake.images import shrink_to_jpeg
from app.reading.claude import ReadResult
from app.reading.schema import LabelReading
from app.rules.application import Application
from app.rules.verdict import LabelResult, check_label


class LabelReader(Protocol):
    async def read(self, images: list[bytes]) -> ReadResult: ...


class NotAnImage(ValueError):
    """An uploaded file could not be opened as an image."""

    def __init__(self, name: str):
        super().__init__(f'"{name}" is not an image this app can read.')
        self.name = name


@dataclass(frozen=True)
class CheckOutcome:
    result: LabelResult
    reading: LabelReading
    images: list[bytes]  # the shrunken JPEGs, kept only to show in the response
    seconds: float  # from receiving the images to the finished result
    reading_seconds: float


async def check_one(
    application: Application,
    images: list[tuple[str, bytes]],
    reader: LabelReader,
    max_edge: int,
) -> CheckOutcome:
    """Check one product's label images, given as (file name, bytes), against its application."""
    start = time.perf_counter()
    prepared = []
    for name, data in images:
        try:
            # Image work is slow Python code, so it runs off the event loop.
            prepared.append(await asyncio.to_thread(shrink_to_jpeg, data, max_edge))
        except (UnidentifiedImageError, OSError) as error:
            raise NotAnImage(name) from error
    read = await reader.read(prepared)
    result = check_label(application, read.reading)
    return CheckOutcome(
        result=result,
        reading=read.reading,
        images=prepared,
        seconds=time.perf_counter() - start,
        reading_seconds=read.seconds,
    )
