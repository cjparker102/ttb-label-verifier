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


@pytest.mark.parametrize(
    ("application", "label"),
    [
        ("16.9 fl oz", "16.9 FL. OZ. (500 mL)"),
        ("500 mL", "16.9 FL. OZ. (500 mL)"),
        ("750 mL", "750 mL (25.4 FL. OZ.)"),
        ("25.4 fl oz", "750 mL (25.4 FL. OZ.)"),
    ],
)
def test_a_label_with_both_systems_is_compared_in_the_applications_units(application, label):
    result = check_net_contents(application, read(label))
    assert (result.status, result.note) == (Status.PASS, None)


def test_both_systems_still_catch_a_real_difference():
    result = check_net_contents("12 fl oz", read("16.9 FL. OZ. (500 mL)"))
    assert result.status == Status.FAIL


# Found on approved labels in TTB's Public COLA Registry.


@pytest.mark.parametrize(
    ("text", "ml"),
    [
        ("5.16 US GALS", "19532.7"),  # "US" before the unit, and "GALS"
        ("12 U.S. FL. OZ.", "354.9"),
        ("1L 40% vol, 1 liter", "1000"),  # the same size twice counts once
        ("750 mL ... 750 ML", "750"),
        ("1 PINT 9 FL OZ", "739.3"),  # falling units still add up
    ],
)
def test_one_amount(text, ml):
    assert parse_volume(text).ml.quantize(Decimal("0.1")) == Decimal(ml)


def test_several_sizes_are_a_list_to_choose_from():
    volume = parse_volume("15.5 Gallons 7.75 Gallons 5.16 Gallons")
    assert [round(ml) for ml in volume.sizes] == [58674, 29337, 19533]


def test_one_of_several_sizes_needs_review():
    label = read("15.5 GALLONS (HALF BARREL) 5.16 GALLONS (SIXTH BARREL)")
    result = check_net_contents("5.16 gallons", label)
    assert result.status == Status.REVIEW
    assert "which one the label marks" in result.reason


def test_none_of_several_sizes_fails():
    result = check_net_contents("13.2 gallons", read("15.5 Gallons 7.75 Gallons 5.16 Gallons"))
    assert result.status == Status.FAIL
    assert "none of them" in result.reason


# The same amount written in two units counts once (found on approved labels in TTB's
# Public COLA Registry: "1 pint (16 fl oz)" was added up to 2 pints).


@pytest.mark.parametrize(
    ("text", "ml"),
    [
        ("12 FL OZ (355 mL)", "355"),  # two systems: metric counts
        ("1 PINT (16 FL OZ)", "473.2"),
        ("CONTENTS 1 PINT (16 FL. OZ)", "473.2"),
        ("1 QUART (32 FL OZ)", "946.4"),
        ("750 mL (25.4 FL OZ)", "750"),
        ("1 PINT 9 FL OZ", "739.3"),  # a pint and 9 fluid ounces more still add up
        ("1 GAL 1 QT", "4731.8"),
    ],
)
def test_the_same_amount_in_two_units(text, ml):
    assert parse_volume(text).ml.quantize(Decimal("0.1")) == Decimal(ml)


@pytest.mark.parametrize(
    ("label", "application"),
    [
        ("12 FL OZ (355 mL)", "12 fl oz"),
        ("12 FL OZ (355 mL)", "355 mL"),
        ("1 PINT (16 FL OZ)", "1 pint"),
        ("1 PINT (16 FL OZ)", "16 fl oz"),
        ("750 mL (25.4 FL OZ)", "750 mL"),
        ("750 mL (25.4 FL OZ)", "25.4 fl oz"),
        ("1 PINT 9 FL OZ", "25 fl oz"),
    ],
)
def test_common_forms_match_the_application(label, application):
    assert check_net_contents(application, read(label)).status == Status.PASS


@pytest.mark.parametrize(
    ("label", "application"),
    [
        ("1 PINT (16 FL OZ)", "2 pints"),
        ("1 PINT (16 FL OZ)", "12 fl oz"),
        ("1 PINT 9 FL OZ", "1 pint"),
    ],
)
def test_a_different_amount_still_fails(label, application):
    assert check_net_contents(application, read(label)).status == Status.FAIL
