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


def perfect_reading(truth: dict) -> LabelReading:
    """What a reader that makes no mistakes would return for a sample's printed text
    (the "truth" entries in samples/expected.json)."""
    fields = {}
    for name, printed in truth.items():
        found = printed["text"] is not None
        fields[name] = {
            "text": printed["text"],
            "readability": "clear" if found else "not_found",
            "image_number": printed["image_number"],
            "english_meaning": None,
        }
    warning = truth["government_warning"]
    fields["government_warning"]["heading_bold"] = "yes" if warning.get("heading_bold") else "no"
    fields["government_warning"]["rest_bold"] = "no"
    return LabelReading.model_validate({**fields, "image_problems": []})


class PerfectReader:
    """Returns perfect readings of the given samples, one per call, in order. Use it
    only where labels are read one at a time, so the order is certain."""

    def __init__(self, truths: list[dict]):
        self.readings = [perfect_reading(truth) for truth in truths]

    async def read(self, images: list[bytes]) -> ReadResult:
        return ReadResult(self.readings.pop(0), seconds=0.01, input_tokens=0, output_tokens=0)


def expected_word(field) -> str:
    """A field result in the words samples/expected.json uses."""
    if field.status == "pass" and field.notes:
        return "pass_with_note"
    return str(field.status)
