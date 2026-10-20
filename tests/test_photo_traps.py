"""Three things a real photo of a bottle tripped over (Oct 20, 2026), reproduced by the
code-drawn sample "vesperly-wine-specialty": the AI reader read the warning from "(1)" on,
leaving out a heading printed on a line of its own; took the fanciful name for the class,
which is printed small on the back; and dropped "ALC." from the alcohol statement. The
pictures are the sample's, and Tesseract really reads them; only the AI reader's mistakes
are stood in."""

import asyncio

import pytest

import app.checking
from app.checking import check_one
from app.reading.ocr import tesseract_available
from app.rules.application import Application, BeverageType
from app.rules.results import Status
from app.rules.warning import GOVERNMENT_WARNING
from tests.stand_ins import ReplayReader, expected_word, perfect_reading
from tools.evaluate import load_entries
from tools.make_samples import LABELS_DIR, sample_for

ENTRY = load_entries(["vesperly-wine-specialty"])[0]
SAMPLE = sample_for(ENTRY["id"])
APPLICATION = Application(BeverageType.from_text(SAMPLE.beverage_type), **SAMPLE.application)
PICTURES = [(name, (LABELS_DIR / name).read_bytes()) for name in ENTRY["images"]]


def misread(alcohol="ALC. 5% BY VOL"):
    """The sample read with the photo's mistakes."""
    reading = perfect_reading(ENTRY["truth"]).model_copy(deep=True)
    reading.government_warning.text = GOVERNMENT_WARNING.removeprefix("GOVERNMENT WARNING: ")
    reading.class_type.text, reading.class_type.image_number = "MOONLIT BRAMBLE", 1
    reading.alcohol_content.text = alcohol
    return reading


def fields(reading, **options):
    outcome = asyncio.run(check_one(APPLICATION, PICTURES, ReplayReader(reading), 1568, **options))
    return {field.field: field for field in outcome.result.fields}


def test_the_sample_shows_all_three_patterns():
    truth = ENTRY["truth"]
    assert truth["class_type"] == {"text": "WINE SPECIALTY", "image_number": 2}
    assert truth["alcohol_content"]["text"] == "ALC. 5% BY VOL"
    assert truth["government_warning"]["text"] == GOVERNMENT_WARNING  # heading apart, but printed
    assert set(ENTRY["expected"].values()) <= {"pass", "pass_with_note", "not_needed"}  # no flaw


def test_read_correctly_every_field_matches():
    got = fields(perfect_reading(ENTRY["truth"]))
    assert {name: expected_word(field) for name, field in got.items()} == ENTRY["expected"]


@pytest.mark.skipif(not tesseract_available(), reason="Tesseract is not installed")
@pytest.mark.parametrize("batch", [False, True], ids=["single check", "batch"])
def test_the_heading_and_class_are_found_where_the_ai_reader_missed_them(monkeypatch, batch):
    monkeypatch.setattr(app.checking, "OUTLINE_WAIT", 60)  # Tesseract's words, however slow
    options = {"warning_only": True} if batch else {"outline": True}
    got = fields(misread(), **options)
    warning, class_type = got["government_warning"], got["class_type"]
    assert warning.status == Status.PASS
    assert any(
        "found by basic text reading, so it counts as present" in c.reason for c in warning.checks
    )
    assert class_type.status == Status.PASS
    assert class_type.label_says == "Wine Specialty"
    assert class_type.checks[0].note == "Matches, found on image 2"


def test_without_a_second_reading_a_missing_heading_is_check_this_not_a_problem():
    got = fields(misread())  # no Tesseract words
    assert got["government_warning"].status == Status.REVIEW
    assert got["class_type"].status == Status.FAIL  # nothing else to find the class with


def test_the_alcohol_statement_must_be_read_whole():
    # The reader is told to copy every word of it (tests/reading/test_claude.py), because
    # the form TTB allows for wine needs the word for alcohol.
    assert fields(misread())["alcohol_content"].status == Status.PASS
    shortened = fields(misread(alcohol="5% BY VOL"))["alcohol_content"]
    assert shortened.status == Status.REVIEW
    assert "not in one of the forms TTB allows" in shortened.checks[-1].reason
