import dataclasses

import pytest

from app.reading.schema import LabelReading
from app.rules import citations as cfr
from app.rules.application import Application, BeverageType
from app.rules.results import Citation, Status
from app.rules.ttb import (
    alcohol_checks,
    bottler_checks,
    english_checks,
    net_contents_checks,
    same_side_checks,
    ttb_checks,
)
from app.rules.warning import GOVERNMENT_WARNING
from tests.rules.helpers import read, read_warning

SPIRITS = BeverageType.DISTILLED_SPIRITS
WINE = BeverageType.WINE
MALT = BeverageType.MALT_BEVERAGE


def label(**fields):
    """A clean label reading, with any fields replaced."""
    base = {
        "brand_name": read("OLD TOM DISTILLERY"),
        "class_type": read("Kentucky Straight Bourbon Whiskey"),
        "alcohol_content": read("45% Alc./Vol. (90 Proof)"),
        "net_contents": read("750 mL"),
        "bottler_name_address": read("Bottled by Old Tom Distillery, Bardstown, Kentucky"),
        "country_of_origin": read(None),
        "government_warning": read_warning(GOVERNMENT_WARNING),
        "image_problems": [],
    }
    return LabelReading(**{**base, **fields})


def statuses(checks):
    return [check.status for check in checks]


# Alcohol content


def test_spirits_must_state_alcohol_content():
    checks = alcohol_checks(SPIRITS, label(alcohol_content=read(None)))
    assert statuses(checks) == [Status.FAIL]
    assert checks[0].citation == cfr.SPIRITS_ALCOHOL_REQUIRED


def test_wine_must_state_alcohol_content_unless_table_or_light_wine():
    assert statuses(
        alcohol_checks(WINE, label(class_type=read("Red Wine"), alcohol_content=read(None)))
    ) == [Status.FAIL]
    for designation in ("Table Wine", "Light Wine", "Red Table Wine"):
        reading = label(class_type=read(designation), alcohol_content=read(None))
        assert alcohol_checks(WINE, reading) == []


def test_malt_beverages_may_leave_out_alcohol_content():
    assert alcohol_checks(MALT, label(alcohol_content=read(None))) == []


@pytest.mark.parametrize(
    ("beverage", "text"),
    [
        # The examples given in 27 CFR 5.65(b)(4) and 7.65(b)(5).
        (SPIRITS, "40% alc/vol"),
        (SPIRITS, "Alc. 40 percent by vol."),
        (SPIRITS, "Alc 40% by vol"),
        (SPIRITS, "40% Alcohol by Volume."),
        (SPIRITS, "45% Alc./Vol. (90 Proof)"),
        (MALT, "4.2% alc/vol"),
        (MALT, "Alc. 4.0 percent by vol."),
        (MALT, "Alc 4% by vol"),
        (MALT, "5.9% Alcohol by Volume."),
        # 27 CFR 4.36(b)(1): "Alcohol __ % by volume," with "alc." and "vol." allowed.
        (WINE, "Alcohol 13.5% by volume"),
        (WINE, "Alc. 12.5% by vol."),
    ],
)
def test_allowed_alcohol_forms_pass(beverage, text):
    assert statuses(alcohol_checks(beverage, label(alcohol_content=read(text)))) == [Status.PASS]


@pytest.mark.parametrize(
    ("beverage", "text"),
    [(SPIRITS, "45% ABV"), (MALT, "5.6%"), (WINE, "13,5% vol")],
)
def test_other_alcohol_forms_need_review(beverage, text):
    checks = alcohol_checks(beverage, label(alcohol_content=read(text)))
    assert statuses(checks) == [Status.REVIEW]


def test_proof_alone_fails():
    checks = alcohol_checks(SPIRITS, label(alcohol_content=read("90 Proof")))
    assert statuses(checks) == [Status.FAIL]
    assert checks[0].citation == cfr.SPIRITS_ALCOHOL_FORM


def test_hard_to_read_alcohol_is_left_to_the_match_check():
    reading = label(alcohol_content=read("45% Alc./Vol.", readability="unclear"))
    assert alcohol_checks(SPIRITS, reading) == []


# Net contents


@pytest.mark.parametrize(
    ("beverage", "text", "expected"),
    [
        (SPIRITS, "750 mL", [Status.PASS, Status.PASS]),
        (SPIRITS, "1.75 L", [Status.PASS, Status.PASS]),
        (SPIRITS, "1 L", [Status.PASS, Status.PASS]),
        (SPIRITS, "700 mL", [Status.PASS, Status.PASS]),  # added Jan 2025
        (SPIRITS, "740 mL", [Status.PASS, Status.FAIL]),
        (SPIRITS, "25.4 FL. OZ.", [Status.FAIL]),
        (SPIRITS, "75 cl", [Status.REVIEW]),
        (SPIRITS, "750 mL (25.4 FL. OZ.)", [Status.PASS, Status.PASS]),
        (WINE, "750 ml", [Status.PASS, Status.PASS]),
        (WINE, "568 mL", [Status.PASS, Status.PASS]),
        (WINE, "710 mL", [Status.PASS, Status.FAIL]),  # a spirits size, not a wine size
        (WINE, "4 L", [Status.PASS, Status.PASS]),  # even liters from 4 L up
        (WINE, "4.5 L", [Status.PASS, Status.FAIL]),
        (MALT, "12 FL. OZ.", [Status.PASS]),
        (MALT, "1 PINT 8 FL OZ", [Status.PASS]),
        (MALT, "355 mL (12 FL OZ)", [Status.PASS]),
        (MALT, "355 mL", [Status.FAIL]),
    ],
)
def test_net_contents_units_and_sizes(beverage, text, expected):
    assert statuses(net_contents_checks(beverage, label(net_contents=read(text)))) == expected


def test_container_size_failure_names_the_size_and_rule():
    checks = net_contents_checks(SPIRITS, label(net_contents=read("740 mL")))
    assert checks[1].reason == "740 mL is not an authorized container size for distilled spirits."
    assert checks[1].citation == cfr.SPIRITS_SIZES


# Same side of the bottle


def test_spirits_brand_type_and_alcohol_on_one_image_pass():
    assert statuses(same_side_checks(SPIRITS, label())) == [Status.PASS]


def test_spirits_brand_type_and_alcohol_on_different_images_need_review():
    reading = label(alcohol_content=read("45% Alc./Vol.", image_number=2))
    checks = same_side_checks(SPIRITS, reading)
    assert statuses(checks) == [Status.REVIEW]
    assert checks[0].citation == cfr.SPIRITS_SAME_SIDE


def test_same_side_rule_is_only_for_spirits():
    reading = label(alcohol_content=read("5% alc/vol", image_number=2))
    assert same_side_checks(WINE, reading) == same_side_checks(MALT, reading) == []


# Bottler and importer statements


@pytest.mark.parametrize(
    ("beverage", "is_import", "text", "expected"),
    [
        (SPIRITS, False, "Bottled by Old Tom Distillery, Bardstown, Kentucky", [Status.PASS]),
        (SPIRITS, False, "Distilled by Old Tom Distillery, Bardstown, Kentucky", [Status.PASS]),
        (SPIRITS, False, "Bottled for Old Tom Distillery, Bardstown, Kentucky", [Status.PASS]),
        (SPIRITS, False, "Old Tom Distillery, Bardstown, Kentucky", [Status.REVIEW]),
        (SPIRITS, True, "Imported by Landrevin Imports, New York, NY", [Status.PASS]),
        (SPIRITS, True, "Bottled by Landrevin Imports, New York, NY", [Status.PASS]),
        (SPIRITS, True, "Landrevin Imports, New York, NY", [Status.REVIEW]),
        (WINE, False, "Bottled by Landrevin Cellars, Napa, CA", [Status.PASS]),
        (WINE, False, "Produced and bottled by Landrevin Cellars, Napa, CA", [Status.PASS]),
        (WINE, False, "Cellared by Landrevin Cellars, Napa, CA", [Status.REVIEW]),
        (WINE, True, "Imported by Landrevin Imports, New York, NY", [Status.PASS]),
        (WINE, True, "Bottled by Landrevin Imports, New York, NY", [Status.REVIEW]),
        (MALT, False, "Tidewick Brewing Co., Norfolk, Virginia", []),  # phrase is optional
        (MALT, True, "Imported by Harbor Beer Imports, Boston, MA", [Status.PASS]),
        (MALT, True, "Harbor Beer Imports, Boston, MA", [Status.REVIEW]),
    ],
)
def test_bottler_statement_wording(beverage, is_import, text, expected):
    reading = label(bottler_name_address=read(text))
    assert statuses(bottler_checks(beverage, reading, is_import)) == expected


# English


def test_non_english_mandatory_information_needs_review():
    reading = label(class_type=read("Vin rouge", english_meaning="Red wine"))
    found = english_checks(WINE, reading)
    assert list(found) == ["class_type"]
    assert found["class_type"][0].citation == cfr.WINE_ENGLISH


def test_brand_name_may_be_in_any_language():
    reading = label(brand_name=read("Château Landrevin", english_meaning="Landrevin Castle"))
    assert english_checks(SPIRITS, reading) == {}


def test_wine_producer_name_may_be_in_another_language_but_spirits_bottler_may_not():
    bottler = read("Mis en bouteille par Landrevin", english_meaning="Bottled by Landrevin")
    reading = label(bottler_name_address=bottler)
    assert english_checks(WINE, reading) == {}
    assert list(english_checks(SPIRITS, reading)) == ["bottler_name_address"]


# Putting the rules together


def application(beverage=SPIRITS, country=""):
    return Application(
        beverage, "OLD TOM DISTILLERY", "Bourbon", "45%", "750 mL", "Old Tom", country
    )


def test_import_status_comes_from_the_application_country():
    reading = label(bottler_name_address=read("Bottled by Old Tom Distillery"))
    wine_domestic = ttb_checks(application(WINE, "USA"), reading)["bottler_name_address"]
    wine_import = ttb_checks(application(WINE, "France"), reading)["bottler_name_address"]
    assert statuses(wine_domestic) == [Status.PASS]
    assert statuses(wine_import) == [Status.REVIEW]


def test_every_citation_points_to_the_current_ecfr():
    found = [value for value in vars(cfr).values() if isinstance(value, Citation)]
    assert len(found) >= 20
    for citation in found:
        assert citation.url.startswith("https://www.ecfr.gov/current/title-27/section-")
        assert citation.section.startswith("27 CFR ")
        assert citation.checked == cfr.CHECKED


def test_checks_are_frozen():
    check = alcohol_checks(SPIRITS, label())[0]
    with pytest.raises(dataclasses.FrozenInstanceError):
        check.status = Status.FAIL


def test_a_foreign_statement_beside_an_english_importer_statement_is_fine():
    bottler = read(
        "Embotellado por Destilería Cerro, Jalisco Imported by Cerro Imports, San Diego, CA",
        english_meaning="Bottled by Destilería Cerro, Jalisco. Imported by Cerro Imports.",
    )
    reading = label(bottler_name_address=bottler)
    assert english_checks(SPIRITS, reading) == {}
    assert english_checks(MALT, reading) == {}
