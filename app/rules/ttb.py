"""TTB labeling rules that apply whatever the application says (plan section 6b).

These are separate from the match checks: a label can match its application and
still break a rule. Each check cites its eCFR paragraph (see citations.py).
Checks that need a field's text are skipped when the text is missing or hard to
read, because the match checks already report that.
"""

import re
from decimal import Decimal

from app.reading.schema import FieldReading, LabelReading
from app.rules import citations as cfr
from app.rules.alcohol import CannotParse as NoAlcoholFigure
from app.rules.alcohol import parse_alcohol
from app.rules.application import Application, BeverageType
from app.rules.countries import is_domestic
from app.rules.names import LEAD_IN, role, statements
from app.rules.net_contents import CannotParse as NoVolume
from app.rules.net_contents import parse_volume, show_ml
from app.rules.results import Check, Status
from app.rules.text import is_missing, is_unclear, tidy

SPIRITS = BeverageType.DISTILLED_SPIRITS
WINE = BeverageType.WINE
MALT = BeverageType.MALT_BEVERAGE

ALCOHOL_WORD = re.compile(r"\balc(?:ohol)?\b", re.IGNORECASE)
VOLUME_WORD = re.compile(r"\bvol(?:ume)?\b", re.IGNORECASE)
PERCENT_SIGN = re.compile(r"%|\bpercent\b", re.IGNORECASE)
TABLE_OR_LIGHT_WINE = re.compile(r"\b(?:table|light)\b", re.IGNORECASE)
IMPORTED = re.compile(r"\bimport(?:ed|er)\b", re.IGNORECASE)
BOTTLED_OR_PACKED_BY = re.compile(r"\b(?:bottled|packed)\b.*\bby\b", re.IGNORECASE)

ALCOHOL_FORM = {
    SPIRITS: cfr.SPIRITS_ALCOHOL_FORM,
    WINE: cfr.WINE_ALCOHOL_FORM,
    MALT: cfr.MALT_ALCOHOL_FORM,
}
ALCOHOL_EXAMPLE = {SPIRITS: "40% alc/vol", WINE: "Alcohol 12% by volume", MALT: "4.2% alc/vol"}
NAMES = {SPIRITS: "Distilled spirits", WINE: "Wine", MALT: "Malt beverage"}

METRIC = {"mL", "L"}
US_UNITS = {"fl oz", "pint", "quart", "gallon"}
SPIRITS_SIZES_ML = {
    Decimal(ml)
    for ml in "3750 3000 2000 1800 1750 1500 1000 945 900 750 720 710 700 570 500 475 "
    "375 355 350 331 250 200 187 100 50".split()
}
WINE_SIZES_ML = {
    Decimal(ml)
    for ml in "3000 2250 1800 1500 1000 750 720 700 620 600 568 550 500 473 375 360 355 "
    "330 300 250 200 187 180 100 50".split()
}
SIZE_TOLERANCE_ML = Decimal("0.5")


def readable(field: FieldReading) -> str | None:
    if is_missing(field) or is_unclear(field):
        return None
    return tidy(field.text or "")


def alcohol_may_be_left_out(beverage: BeverageType, reading: LabelReading) -> bool:
    """Wine at 14% or less labeled "table" or "light" wine (4.36(a)), and malt
    beverages unless alcohol comes from added flavors (7.63(a)(3)), which the
    application doesn't tell us."""
    if beverage == MALT:
        return True
    return beverage == WINE and bool(TABLE_OR_LIGHT_WINE.search(reading.class_type.text or ""))


def alcohol_checks(beverage: BeverageType, reading: LabelReading) -> list[Check]:
    field = reading.alcohol_content
    if is_missing(field):
        if beverage == SPIRITS:
            return [
                Check(
                    Status.FAIL,
                    "Distilled spirits labels must state the alcohol content.",
                    citation=cfr.SPIRITS_ALCOHOL_REQUIRED,
                )
            ]
        if beverage == WINE and not alcohol_may_be_left_out(beverage, reading):
            return [
                Check(
                    Status.FAIL,
                    "Wine labels must state the alcohol content, unless the class or type "
                    'is "table wine" or "light wine" (for wine of 14% or less).',
                    citation=cfr.WINE_ALCOHOL_REQUIRED,
                )
            ]
        return []

    text = readable(field)
    if text is None:
        return []
    try:
        statement = parse_alcohol(text)
    except NoAlcoholFigure:
        return []
    rule = ALCOHOL_FORM[beverage]
    if statement.abv is None:
        return [
            Check(
                Status.FAIL,
                "The alcohol content must be stated as a percentage of alcohol by volume. "
                "Proof alone is not enough.",
                citation=rule,
            )
        ]
    if not (ALCOHOL_WORD.search(text) and VOLUME_WORD.search(text) and PERCENT_SIGN.search(text)):
        return [
            Check(
                Status.REVIEW,
                f'"{text}" is not in one of the forms TTB allows for alcohol content, such as '
                f'"{ALCOHOL_EXAMPLE[beverage]}". Please check.',
                citation=rule,
            )
        ]
    return [Check(Status.PASS, "The alcohol content is in a form TTB allows.", citation=rule)]


def net_contents_checks(beverage: BeverageType, reading: LabelReading) -> list[Check]:
    text = readable(reading.net_contents)
    if text is None:
        return []
    try:
        volume = parse_volume(text)
    except NoVolume:
        return []
    written = set(volume.all_units)

    if beverage == MALT:
        if written & US_UNITS:
            return [
                Check(Status.PASS, "The net contents use US units.", citation=cfr.MALT_NET_CONTENTS)
            ]
        return [
            Check(
                Status.FAIL,
                "Malt beverages must state net contents in US units (fluid ounces, pints, "
                "quarts, or gallons). Metric units may only be added alongside them.",
                citation=cfr.MALT_NET_CONTENTS,
            )
        ]

    units_rule = cfr.SPIRITS_NET_CONTENTS if beverage == SPIRITS else cfr.WINE_NET_CONTENTS
    if not written & METRIC:
        if "cl" in written:
            return [
                Check(
                    Status.REVIEW,
                    f'"{text}": net contents must be stated in milliliters or liters. '
                    "Centiliters may only be added alongside them. Please check.",
                    citation=units_rule,
                )
            ]
        return [
            Check(
                Status.FAIL,
                f"{NAMES[beverage]} must state net contents in metric units (mL or L). "
                "US units may only be added alongside them.",
                citation=units_rule,
            )
        ]
    checks = [Check(Status.PASS, "The net contents use metric units.", citation=units_rule)]

    if beverage == SPIRITS:
        sizes, sizes_rule = SPIRITS_SIZES_ML, cfr.SPIRITS_SIZES
        authorized = any(abs(volume.ml - size) <= SIZE_TOLERANCE_ML for size in sizes)
    else:
        sizes, sizes_rule = WINE_SIZES_ML, cfr.WINE_SIZES
        even_liters = volume.ml >= 4000 and volume.ml % 1000 == 0
        authorized = even_liters or any(
            abs(volume.ml - size) <= SIZE_TOLERANCE_ML for size in sizes
        )
    if authorized:
        checks.append(
            Check(
                Status.PASS,
                f"{show_ml(volume.ml)} is an authorized container size.",
                citation=sizes_rule,
            )
        )
    else:
        checks.append(
            Check(
                Status.FAIL,
                f"{show_ml(volume.ml)} is not an authorized container size for "
                f"{NAMES[beverage].lower()}.",
                citation=sizes_rule,
            )
        )
    return checks


def same_side_checks(beverage: BeverageType, reading: LabelReading) -> list[Check]:
    if beverage != SPIRITS:
        return []
    fields = (reading.brand_name, reading.class_type, reading.alcohol_content)
    if any(is_missing(field) for field in fields):
        return []
    if len({field.image_number for field in fields}) == 1:
        return [
            Check(
                Status.PASS,
                "Brand name, class/type, and alcohol content are on the same image.",
                citation=cfr.SPIRITS_SAME_SIDE,
            )
        ]
    return [
        Check(
            Status.REVIEW,
            "Brand name, class/type, and alcohol content must be on the same side of the "
            "bottle, but they were found on different images. Please check.",
            citation=cfr.SPIRITS_SAME_SIDE,
        )
    ]


def bottler_checks(beverage: BeverageType, reading: LabelReading, is_import: bool) -> list[Check]:
    text = readable(reading.bottler_name_address)
    if text is None:
        return []
    if is_import:
        rule = {SPIRITS: cfr.SPIRITS_IMPORTER, WINE: cfr.WINE_IMPORTER, MALT: cfr.MALT_IMPORTER}
        # Spirits bottled in the US after import may say "Bottled by" instead (5.67(b)).
        allowed = IMPORTED.search(text) or (beverage == SPIRITS and LEAD_IN.match(text))
        if allowed:
            return [
                Check(
                    Status.PASS,
                    "The importer statement is worded as required.",
                    citation=rule[beverage],
                )
            ]
        return [
            Check(
                Status.REVIEW,
                'Imported products must name the importer after words such as "Imported by". '
                "Please check.",
                citation=rule[beverage],
            )
        ]
    if beverage == SPIRITS:
        if LEAD_IN.match(text):
            return [
                Check(
                    Status.PASS,
                    "The bottler statement is worded as required.",
                    citation=cfr.SPIRITS_BOTTLER,
                )
            ]
        return [
            Check(
                Status.REVIEW,
                'The name must follow words that say what the company did, such as "Bottled by" '
                'or "Distilled by". Please check.',
                citation=cfr.SPIRITS_BOTTLER,
            )
        ]
    if beverage == WINE:
        if BOTTLED_OR_PACKED_BY.search(text):
            return [
                Check(
                    Status.PASS,
                    "The bottler statement is worded as required.",
                    citation=cfr.WINE_BOTTLER,
                )
            ]
        return [
            Check(
                Status.REVIEW,
                'Wine labels must say "Bottled by" or "Packed by" before the name and address. '
                "Please check.",
                citation=cfr.WINE_BOTTLER,
            )
        ]
    return []  # malt beverages: the phrase is optional (7.66(d))


def english_checks(beverage: BeverageType, reading: LabelReading) -> dict[str, list[Check]]:
    """Mandatory information must be in English, except the brand name (and for wine,
    the producer's name). The reader gives an English meaning only for non-English text."""
    rule = {SPIRITS: cfr.SPIRITS_ENGLISH, WINE: cfr.WINE_ENGLISH, MALT: cfr.MALT_ENGLISH}[beverage]
    names = ["class_type", "alcohol_content", "net_contents"]
    if beverage != WINE:
        names.append("bottler_name_address")
    found = {}
    for name in names:
        field = getattr(reading, name)
        text = readable(field)
        if name == "bottler_name_address" and text and any(map(role, statements(text))):
            # One statement says in English what a company did, such as "Imported by".
            # Others beside it may be in another language.
            continue
        if text is not None and field.english_meaning:
            found[name] = [
                Check(
                    Status.REVIEW,
                    f'"{text}" does not look like English. Mandatory information must be in '
                    "English. Please check.",
                    citation=rule,
                )
            ]
    return found


def ttb_checks(application: Application, reading: LabelReading) -> dict[str, list[Check]]:
    """Every TTB rule check for this label, grouped by the field it belongs to."""
    beverage = application.beverage_type
    is_import = not is_domestic(application.country_of_origin)
    checks: dict[str, list[Check]] = {
        "brand_name": same_side_checks(beverage, reading),
        "alcohol_content": alcohol_checks(beverage, reading),
        "net_contents": net_contents_checks(beverage, reading),
        "bottler_name_address": bottler_checks(beverage, reading, is_import),
    }
    for name, more in english_checks(beverage, reading).items():
        checks.setdefault(name, []).extend(more)
    return checks
