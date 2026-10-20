"""End-to-end tests of the rules on the sample labels."""

import json
from pathlib import Path

import pytest

from app.reading.schema import LabelReading
from app.rules.application import Application, BeverageType
from app.rules.results import Status
from app.rules.verdict import check_label
from tests.stand_ins import expected_word, perfect_reading
from tools.make_samples import SAMPLES_DIR, sample_for

RECORDED = Path(__file__).resolve().parent.parent / "fixtures" / "recorded"


def application_for(entry_id: str) -> Application:
    sample = sample_for(entry_id)
    return Application(BeverageType.from_text(sample.beverage_type), **sample.application)


EXPECTED = json.loads((SAMPLES_DIR / "expected.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("entry", EXPECTED, ids=[e["id"] for e in EXPECTED])
def test_each_sample_gets_its_expected_results(entry):
    result = check_label(application_for(entry["id"]), perfect_reading(entry["truth"]))
    got = {field.field: expected_word(field) for field in result.fields}
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


def test_disagreeing_statements_reach_the_fields():
    """The reader lists every alcohol and net contents statement it saw. If they disagree,
    the field needs review, even when the one it chose matches the application."""
    entry = next(e for e in EXPECTED if e["id"] == "old-tom-bourbon")
    reading = perfect_reading(entry["truth"]).model_copy(
        update={
            "alcohol_statements": ["45% Alc./Vol. (90 Proof)", "43% Alc./Vol."],
            "net_contents_statements": ["750 mL", "75 mL"],
        }
    )
    fields = {f.field: f for f in check_label(application_for(entry["id"]), reading).fields}
    assert fields["alcohol_content"].status == Status.REVIEW
    assert fields["net_contents"].status == Status.REVIEW
    agreeing = reading.model_copy(
        update={"alcohol_statements": ["45% Alc./Vol. (90 Proof)"], "net_contents_statements": []}
    )
    fields = {f.field: f for f in check_label(application_for(entry["id"]), agreeing).fields}
    assert fields["alcohol_content"].status == Status.PASS
