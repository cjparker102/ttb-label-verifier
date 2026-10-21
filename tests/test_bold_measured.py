"""The AI reader's "bold" is checked by measuring the heading's strokes on the picture.
The pictures are the samples', and Tesseract really reads them; only the AI reader's
answer is stood in, including its known slip: calling the heading that isn't bold, bold."""

import asyncio

import pytest

import app.checking
from app.checking import check_one
from app.reading.ocr import tesseract_available
from app.rules.application import Application, BeverageType
from app.rules.results import Status
from app.rules.warning import NOT_CONFIRMED
from tests.stand_ins import ReplayReader, perfect_reading
from tools.batch_live import jpeg, quality_for, with_grain
from tools.evaluate import load_entries
from tools.make_samples import LABELS_DIR, sample_for

needs_tesseract = pytest.mark.skipif(not tesseract_available(), reason="Tesseract is not installed")
MODES = pytest.mark.parametrize(
    "options", [{"outline": True}, {"warning_only": True}], ids=["single check", "batch"]
)


def camera_copy(picture: bytes) -> bytes:
    """The picture with grain, saved as a JPEG of about 0.9 MB, as a camera might."""
    image = with_grain(picture)
    return jpeg(image, quality_for(image, 900_000))


def warning_of(sample_id, heading_bold="yes", camera=False, **options):
    """The warning's checks for a sample read perfectly, but with the AI reader's bold.
    With `camera`, its picture is a grainy, compressed copy."""
    entry = load_entries([sample_id])[0]
    sample = sample_for(sample_id)
    application = Application(BeverageType.from_text(sample.beverage_type), **sample.application)
    pictures = [(name, (LABELS_DIR / name).read_bytes()) for name in entry["images"]]
    if camera:
        pictures = [(name, camera_copy(data)) for name, data in pictures]
    reading = perfect_reading(entry["truth"]).model_copy(deep=True)
    reading.government_warning.heading_bold = heading_bold
    outcome = asyncio.run(check_one(application, pictures, ReplayReader(reading), 1568, **options))
    return next(f for f in outcome.result.fields if f.field == "government_warning")


@pytest.fixture
def patient(monkeypatch):
    monkeypatch.setattr(app.checking, "OUTLINE_WAIT", 60)  # Tesseract's words, however slow


@needs_tesseract
@MODES
def test_a_heading_that_isnt_bold_needs_review_even_when_the_ai_reader_calls_it_bold(
    patient, options
):
    warning = warning_of("northvale-whisky-warning-not-bold", **options)
    assert warning.status == Status.REVIEW
    assert any("looks bold to the AI, but measured" in c.reason for c in warning.checks)


@needs_tesseract
@pytest.mark.parametrize("copy", range(3))
def test_a_heading_that_isnt_bold_needs_review_on_camera_like_copies_too(patient, copy):
    # A grainy, compressed copy measures a little heavier than the drawn picture: up to 1.10
    # times. A live batch of such copies once let one through at the old 1.1 setting.
    warning = warning_of("northvale-whisky-warning-not-bold", camera=True, warning_only=True)
    assert warning.status == Status.REVIEW


@needs_tesseract
@MODES
@pytest.mark.parametrize("camera", [False, True], ids=["drawn", "camera-like copy"])
def test_a_bold_heading_the_ai_reader_calls_bold_is_met(patient, options, camera):
    warning = warning_of("old-tom-bourbon", camera=camera, **options)
    assert warning.status == Status.PASS
    assert warning.notes == [] and all(check.confirmed for check in warning.checks)


@needs_tesseract
@pytest.mark.parametrize("sample_id", ["old-tom-bourbon", "northvale-whisky-warning-not-bold"])
def test_the_ai_readers_doubt_is_check_this_whatever_is_measured(patient, sample_id):
    assert warning_of(sample_id, "cant_tell", outline=True).status == Status.REVIEW


def test_without_the_second_reading_bold_is_not_confirmed():
    warning = warning_of("northvale-whisky-warning-not-bold")  # no Tesseract asked for
    assert warning.status == Status.PASS
    assert warning.notes == ["Matches, bold not confirmed"]
    assert NOT_CONFIRMED in [check.reason for check in warning.checks]


@needs_tesseract
def test_a_failed_measurement_never_stops_a_check(patient, monkeypatch):
    def broken(picture, passes):
        raise ValueError("broken")

    monkeypatch.setattr(app.checking, "heading_weight", broken)
    warning = warning_of("old-tom-bourbon", outline=True)
    assert warning.status == Status.PASS and warning.notes == ["Matches, bold not confirmed"]
