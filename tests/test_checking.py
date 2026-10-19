import asyncio
import json
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from app.checking import NotAnImage, check_one
from app.config import Settings, load_settings
from app.reading.claude import ReadResult
from app.reading.schema import LabelReading
from app.rules.application import Application, BeverageType
from app.rules.results import Status

RECORDED = Path(__file__).resolve().parent / "fixtures" / "recorded" / "old-tom-bourbon.json"
OLD_TOM = Application(
    BeverageType.DISTILLED_SPIRITS,
    "OLD TOM DISTILLERY",
    "Kentucky Straight Bourbon Whiskey",
    "45% Alc./Vol. (90 Proof)",
    "750 mL",
    "Old Tom Distillery, Bardstown, Kentucky",
)


class ReplayReader:
    """Stands in for Claude: returns a reading recorded from a real run."""

    def __init__(self):
        recorded = json.loads(RECORDED.read_text(encoding="utf-8"))
        self.reading = LabelReading.model_validate(recorded["reading"])
        self.received = []

    async def read(self, images):
        self.received.append(images)
        return ReadResult(self.reading, seconds=0.01, input_tokens=0, output_tokens=0)


def png(width=3000, height=2000):
    out = BytesIO()
    Image.new("RGB", (width, height), "white").save(out, format="PNG")
    return out.getvalue()


def test_check_one_shrinks_reads_and_decides():
    reader = ReplayReader()
    images = [("front.png", png()), ("back.png", png())]
    outcome = asyncio.run(check_one(OLD_TOM, images, reader, max_edge=1568))
    assert outcome.result.status == Status.PASS
    assert len(reader.received[0]) == 2
    for jpeg in reader.received[0]:
        assert max(Image.open(BytesIO(jpeg)).size) == 1568
    assert outcome.seconds >= outcome.reading_seconds


def test_a_file_that_is_not_an_image_is_named():
    with pytest.raises(NotAnImage) as raised:
        asyncio.run(check_one(OLD_TOM, [("notes.txt", b"hello")], ReplayReader(), 1568))
    assert raised.value.name == "notes.txt"


def test_default_settings_match_the_timing_test_choices():
    settings = load_settings({})
    assert settings == Settings()
    assert (settings.max_image_edge, settings.thinking, settings.effort) == (1568, False, "low")


def test_settings_come_from_environment_variables():
    settings = load_settings(
        {"CLAUDE_THINKING": "adaptive", "MAX_IMAGE_EDGE": "2576", "CLAUDE_EFFORT": "medium"}
    )
    assert (settings.thinking, settings.max_image_edge, settings.effort) == (True, 2576, "medium")


def test_unknown_thinking_setting_is_refused():
    with pytest.raises(ValueError):
        load_settings({"CLAUDE_THINKING": "sometimes"})
