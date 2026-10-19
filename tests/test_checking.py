import asyncio
from io import BytesIO

import pytest
from PIL import Image

from app.checking import NotAnImage, check_one
from app.config import Settings, load_settings
from app.rules.application import Application, BeverageType
from app.rules.results import Status
from tests.stand_ins import ReplayReader

OLD_TOM = Application(
    BeverageType.DISTILLED_SPIRITS,
    "OLD TOM DISTILLERY",
    "Kentucky Straight Bourbon Whiskey",
    "45% Alc./Vol. (90 Proof)",
    "750 mL",
    "Old Tom Distillery, Bardstown, Kentucky",
)


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
        {
            "TTB_CLAUDE_THINKING": "adaptive",
            "TTB_MAX_IMAGE_EDGE": "2576",
            "TTB_CLAUDE_EFFORT": "xhigh",
        }
    )
    assert (settings.thinking, settings.max_image_edge, settings.effort) == (True, 2576, "xhigh")


def test_other_tools_variables_are_ignored():
    # Claude Code sets CLAUDE_EFFORT in its own shells; the app must not pick it up.
    assert load_settings({"CLAUDE_EFFORT": "xhigh", "CLAUDE_MODEL": "other"}) == Settings()


@pytest.mark.parametrize(
    "env",
    [
        {"TTB_CLAUDE_THINKING": "sometimes"},
        {"TTB_CLAUDE_EFFORT": "extreme"},
        # Thinking off only works up to high effort on Claude Haiku 5.5.
        {"TTB_CLAUDE_THINKING": "off", "TTB_CLAUDE_EFFORT": "xhigh"},
        {"TTB_CLAUDE_EFFORT": "max"},
    ],
)
def test_bad_settings_stop_the_app_at_startup(env):
    with pytest.raises(ValueError):
        load_settings(env)
