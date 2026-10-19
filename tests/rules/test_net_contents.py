from decimal import Decimal

import pytest

from app.rules.net_contents import CannotParse, check_net_contents, parse_volume
from app.rules.results import Status
from tests.rules.helpers import read


@pytest.mark.parametrize(
    ("text", "ml"),
    [
        ("750 mL", "750"),
        ("750ml", "750"),
        ("75 cl", "750"),
        ("0,75 L", "750"),
        ("1 LITER", "1000"),
        ("1.75 L", "1750"),
        ("1,750 mL", "1750"),  # comma as a thousands separator
        ("750 mL ℮", "750"),
        ("12 FL. OZ.", "354.8823547500"),
        ("12 fl oz", "354.8823547500"),
        ("1 PINT 8 FL OZ", "709.7647095000"),
        ("1 quart", "946.352946"),
        ("1 gallon", "3785.411784"),
        ("750 mL (25.4 FL. OZ.)", "750"),  # metric wins when both are given
    ],
)
def test_parse_volume(text, ml):
    assert parse_volume(text).ml == Decimal(ml)


@pytest.mark.parametrize("text", ["large bottle", "750", "Product of France"])
def test_parse_volume_needs_a_unit(text):
    with pytest.raises(CannotParse):
        parse_volume(text)


@pytest.mark.parametrize(
    ("application", "label", "status", "note"),
    [
        ("750 mL", "750 mL", Status.PASS, None),
        ("750 mL", "750 ml", Status.PASS, None),
        ("1 L", "1 LITER", Status.PASS, None),
        ("12 fl oz", "12 FL. OZ.", Status.PASS, None),
        ("750 mL", "750 mL ℮", Status.PASS, None),
        ("750 mL", "75 cl", Status.PASS, "Matches, different units (75 cl = 750 mL)"),
        ("750 mL", "0,75 L", Status.PASS, "Matches, different units (0,75 L = 750 mL)"),
        ("355 mL", "12 FL. OZ.", Status.PASS, "Matches, different units (12 FL. OZ. = 355 mL)"),
        ("750 mL", "700 mL", Status.FAIL, None),
        ("12 fl oz", "16 FL. OZ.", Status.FAIL, None),
        ("375 mL", "12 FL. OZ.", Status.FAIL, None),
    ],
)
def test_net_contents_matching(application, label, status, note):
    result = check_net_contents(application, read(label))
    assert result.status == status
    assert result.note == note


def test_mismatch_reason_quotes_both():
    result = check_net_contents("750 mL", read("700 mL"))
    assert result.reason == 'The label says "700 mL" but the application says "750 mL".'


def test_mismatch_in_different_units_shows_both_in_ml():
    result = check_net_contents("375 mL", read("12 FL. OZ."))
    assert result.reason.endswith("(354.9 mL vs 375 mL)")


def test_missing_from_label_fails():
    assert check_net_contents("750 mL", read(None)).status == Status.FAIL


@pytest.mark.parametrize(
    ("application", "label"),
    [
        ("", read("750 mL")),
        ("750 mL", read("750 mL", readability="unclear")),
        ("750 mL", read("7[?]0 mL")),
        ("750 mL", read("large bottle")),
        ("one bottle", read("750 mL")),
    ],
)
def test_needs_review(application, label):
    assert check_net_contents(application, label).status == Status.REVIEW
