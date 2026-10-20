"""tools/second_reading.py: what Tesseract's second reading made of a label's warning."""

import json

import pytest

from app.intake.images import shrink_to_jpeg, split_pages
from app.reading.ocr import tesseract_available
from app.rules.warning import GOVERNMENT_WARNING
from tests.stand_ins import perfect_reading
from tools.make_samples import LABELS_DIR, SAMPLES_DIR
from tools.second_reading import outcome

EXPECTED = {e["id"]: e for e in json.loads((SAMPLES_DIR / "expected.json").read_text())}


def pictures(entry):
    return [
        shrink_to_jpeg(data, 1568)
        for name in entry["images"]
        for _, data in split_pages(name, (LABELS_DIR / name).read_bytes())
    ]


@pytest.mark.skipif(not tesseract_available(), reason="Tesseract is not installed")
def test_a_clean_printed_warning_is_read_twice_and_agrees():
    entry = EXPECTED["ridgewick-rye-wrong-abv"]
    reading = perfect_reading(entry["truth"])
    assert outcome(reading, pictures(entry)) == "both passes read it, and agreed with the AI reader"


@pytest.mark.skipif(not tesseract_available(), reason="Tesseract is not installed")
def test_a_warning_the_ai_reader_corrected_is_caught():
    entry = EXPECTED["heronmere-gin-warning-wording"]  # printed with wrong wording
    reading = perfect_reading(entry["truth"]).model_copy(deep=True)
    reading.government_warning.text = GOVERNMENT_WARNING
    assert (
        outcome(reading, pictures(entry)) == "both passes read it, and disagreed with the AI reader"
    )


def test_a_label_without_a_warning_is_counted_apart():
    entry = EXPECTED["driftwood-rum-no-warning"]
    reading = perfect_reading(entry["truth"])
    assert outcome(reading, pictures(entry)) == "no warning read by the AI reader"
