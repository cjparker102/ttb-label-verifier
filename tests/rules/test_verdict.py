"""End-to-end tests of the rules on the sample labels."""

import json
from pathlib import Path

import pytest

from app.reading.schema import LabelReading
from app.rules.application import Application, BeverageType
from app.rules.results import Status
from app.rules.verdict import check_label
from tools.make_samples import SAMPLES, SAMPLES_DIR

RECORDED = Path(__file__).resolve().parent.parent / "fixtures" / "recorded"


def perfect_reading(truth: dict) -> LabelReading:
    """What a reader that makes no mistakes would return for a sample's printed text."""
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


def as_expected(field) -> str:
    """Turn a field result into the words used in samples/expected.json."""
    if field.status == Status.PASS and field.notes:
        return "pass_with_note"
    return str(field.status)


def application_for(sample_id: str) -> Application:
    sample = next(s for s in SAMPLES if s.id == sample_id)
    return Application(BeverageType.from_text(sample.beverage_type), **sample.application)


EXPECTED = json.loads((SAMPLES_DIR / "expected.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("entry", EXPECTED, ids=[e["id"] for e in EXPECTED])
def test_each_sample_gets_its_expected_results(entry):
    result = check_label(application_for(entry["id"]), perfect_reading(entry["truth"]))
    got = {field.field: as_expected(field) for field in result.fields}
    assert got == entry["expected"]


def test_recorded_claude_reading_of_a_clean_label_passes():
    recorded = json.loads((RECORDED / "old-tom-bourbon.json").read_text(encoding="utf-8"))
    reading = LabelReading.model_validate(recorded["reading"])
    result = check_label(application_for("old-tom-bourbon"), reading)
    assert result.status == Status.PASS
    assert {f.field: f.status for f in result.fields}["country_of_origin"] == Status.NOT_NEEDED


def test_label_status_is_the_worst_field_and_counts_add_up():
    entry = next(e for e in EXPECTED if e["id"] == "chateau-landrevin-wine")
    result = check_label(application_for(entry["id"]), perfect_reading(entry["truth"]))
    assert result.status == Status.REVIEW
    assert result.counts[Status.REVIEW] == 2  # accented brand, alcohol statement form
    assert sum(result.counts.values()) == 7


def test_fields_keep_what_each_side_says():
    entry = next(e for e in EXPECTED if e["id"] == "saltreed-vodka-net-contents")
    result = check_label(application_for(entry["id"]), perfect_reading(entry["truth"]))
    net = next(f for f in result.fields if f.field == "net_contents")
    assert (net.application_says, net.label_says, net.image_number) == ("750 mL", "700 mL", 1)


@pytest.mark.parametrize(
    ("text", "beverage_type"),
    [
        ("Distilled spirits", BeverageType.DISTILLED_SPIRITS),
        ("distilled_spirits", BeverageType.DISTILLED_SPIRITS),
        ("  WINE ", BeverageType.WINE),
        ("Malt beverage", BeverageType.MALT_BEVERAGE),
        ("Beer", BeverageType.MALT_BEVERAGE),
    ],
)
def test_beverage_type_from_text(text, beverage_type):
    assert BeverageType.from_text(text) == beverage_type


def test_unknown_beverage_type_is_refused():
    with pytest.raises(ValueError, match="Unknown beverage type"):
        BeverageType.from_text("cider")
