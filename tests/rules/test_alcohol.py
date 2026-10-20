from decimal import Decimal

import pytest

from app.rules.alcohol import CannotParse, check_alcohol, parse_alcohol
from app.rules.results import Status
from tests.rules.helpers import read


@pytest.mark.parametrize(
    ("text", "abv", "proof"),
    [
        ("45% Alc./Vol. (90 Proof)", "45", "90"),
        ("Alc. 45 % by Vol.", "45", None),
        ("13,5% vol", "13.5", None),
        ("Alcohol 13.5 percent by volume", "13.5", None),
        ("5.6% ALC/VOL", "5.6", None),
        ("90 Proof", None, "90"),
        ("86° proof", None, "86"),
        ("45", "45", None),
    ],
)
def test_parse_alcohol(text, abv, proof):
    statement = parse_alcohol(text)
    assert statement.abv == (Decimal(abv) if abv else None)
    assert statement.proof == (Decimal(proof) if proof else None)


@pytest.mark.parametrize("text", ["Alc./Vol.", "40% or 45% Alc./Vol.", "Table Wine"])
def test_parse_alcohol_refuses_missing_or_ambiguous_figures(text):
    with pytest.raises(CannotParse):
        parse_alcohol(text)


@pytest.mark.parametrize(
    ("application", "label", "status"),
    [
        ("45% Alc./Vol. (90 Proof)", "45% Alc./Vol. (90 Proof)", Status.PASS),
        ("45%", "45% Alc./Vol.", Status.PASS),
        ("45", "45% ABV", Status.PASS),
        ("13.5%", "13,5% vol", Status.PASS),
        ("90 Proof", "45% Alc./Vol.", Status.PASS),
        ("4.5%", "4.50% ALC/VOL", Status.PASS),
        ("45.3%", "45.3% Alc./Vol. (91 Proof)", Status.PASS),  # proof rounded to a whole number
        ("45%", "46% Alc./Vol. (92 Proof)", Status.FAIL),
        ("45% Alc./Vol. (90 Proof)", "47% Alc./Vol. (94 Proof)", Status.FAIL),
        ("13.5%", "13.6% vol", Status.FAIL),
        ("45% (90 Proof)", "45% Alc./Vol. (91 Proof)", Status.FAIL),
    ],
)
def test_alcohol_matching(application, label, status):
    assert check_alcohol(application, read(label)).status == status


def test_mismatch_reason_gives_both_numbers():
    result = check_alcohol("45% Alc./Vol. (90 Proof)", read("46% Alc./Vol. (92 Proof)"))
    assert result.reason == "The label says 46% but the application says 45%."


def test_proof_must_be_twice_the_abv():
    result = check_alcohol("40%", read("40% Alc./Vol. (90 Proof)"))
    assert result.status == Status.FAIL
    assert result.reason == "The label says 40% alcohol but 90 proof. 40% alcohol is 80 proof."


def test_missing_from_label_fails_when_the_application_has_it():
    assert check_alcohol("45%", read(None)).status == Status.FAIL


def test_missing_from_both_is_not_needed():
    assert check_alcohol("", read(None)).status == Status.NOT_NEEDED


@pytest.mark.parametrize(
    ("application", "label"),
    [
        ("", read("5.6% ALC/VOL")),  # application blank
        ("45%", read("45% Alc./Vol.", readability="unclear")),
        ("45%", read("4[?]% Alc./Vol.")),
        ("45%", read("Alc./Vol.")),  # no number
        ("about forty", read("45% Alc./Vol.")),  # application has no number
    ],
)
def test_needs_review(application, label):
    assert check_alcohol(application, label).status == Status.REVIEW


def test_label_may_leave_out_alcohol_when_rules_allow_it():
    result = check_alcohol("12%", read(None), optional_on_label=True)
    assert result.status == Status.NOT_NEEDED


# A range is never treated as one number (ChatGPT review, Oct 20, 2026).


@pytest.mark.parametrize(
    "label",
    ["ALC 11-14% BY VOL.", "11 - 14% alc/vol", "Alcohol 11 to 14 percent by volume", "12–13.5%"],
)
def test_an_alcohol_range_needs_review(label):
    for application in ("13%", "14%", "11%", "20%"):
        result = check_alcohol(application, read(label))
        assert result.status == Status.REVIEW
        assert "range of alcohol content" in result.reason


@pytest.mark.parametrize(
    "label", ["2019 - 14% alc/vol", "750 ML - 13% ALC/VOL", "45% Alc./Vol. - 90 Proof"]
)
def test_a_year_or_size_before_a_percentage_is_not_a_range(label):
    assert "range" not in check_alcohol("13%", read(label)).reason
