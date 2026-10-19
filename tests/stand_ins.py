"""Readers that stand in for Claude in tests, so tests run offline and cost nothing."""

import json
from pathlib import Path

from app.reading.claude import ReadingFailed, ReadResult
from app.reading.schema import LabelReading

RECORDED = Path(__file__).resolve().parent / "fixtures" / "recorded"


def recorded_reading(name: str = "old-tom-bourbon") -> LabelReading:
    """A reading recorded from a real Claude run (see tests/fixtures/recorded)."""
    recorded = json.loads((RECORDED / f"{name}.json").read_text(encoding="utf-8"))
    return LabelReading.model_validate(recorded["reading"])


class ReplayReader:
    """Returns a fixed reading and remembers the images it was given."""

    def __init__(self, reading: LabelReading | None = None):
        self.reading = reading or recorded_reading()
        self.received: list[list[bytes]] = []

    async def read(self, images: list[bytes]) -> ReadResult:
        self.received.append(images)
        return ReadResult(self.reading, seconds=0.01, input_tokens=0, output_tokens=0)


class FailingReader:
    async def read(self, images: list[bytes]) -> ReadResult:
        raise ReadingFailed("Claude stopped with reason: refusal")
