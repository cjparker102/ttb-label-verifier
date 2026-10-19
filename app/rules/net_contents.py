"""Matching rules for the net contents statement."""

import re
from dataclasses import dataclass
from decimal import Decimal

from app.reading.schema import FieldReading
from app.rules.results import Check, Status
from app.rules.text import is_missing, is_unclear, tidy

# Unit name, how it is written, milliliters per unit. US units are exact definitions.
UNITS = [
    ("mL", r"millilit(?:er|re)s?|ml", Decimal(1), True),
    ("cl", r"centilit(?:er|re)s?|cl", Decimal(10), True),
    ("L", r"lit(?:er|re)s?|ltr|l", Decimal(1000), True),
    ("fl oz", r"fl(?:uid)?\.?\s*(?:ounces?|oz)\.?|ounces?|oz\.?", Decimal("29.5735295625"), False),
    ("pint", r"pints?|pt\.?", Decimal("473.176473"), False),
    ("quart", r"quarts?|qt\.?", Decimal("946.352946"), False),
    ("gallon", r"gallons?|gal\.?", Decimal("3785.411784"), False),
]
AMOUNT = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*(?:"
    + "|".join(f"(?P<u{i}>{pattern})" for i, (_, pattern, _, _) in enumerate(UNITS))
    + r")(?![a-z])",
    re.IGNORECASE,
)
THOUSANDS = re.compile(r"^[1-9]\d{0,2},\d{3}$")  # 1,750 is one thousand seven hundred fifty

# Converting between units rounds, so allow half a percent.
TOLERANCE = Decimal("0.005")


class CannotParse(ValueError):
    """The statement has no amount with a known unit."""


@dataclass(frozen=True)
class Volume:
    ml: Decimal
    units: tuple[str, ...]  # the units counted, such as ("pint", "fl oz")
    all_units: tuple[str, ...]  # every unit written, including any not counted


def to_number(text: str) -> Decimal:
    if THOUSANDS.match(text):
        return Decimal(text.replace(",", ""))
    return Decimal(text.replace(",", "."))


def parse_volume(text: str) -> Volume:
    """Total volume in mL. When both metric and US units are given, the metric one counts."""
    metric: list[tuple[str, Decimal]] = []
    us: list[tuple[str, Decimal]] = []
    for match in AMOUNT.finditer(text.replace("℮", " ")):
        index = next(i for i in range(len(UNITS)) if match.group(f"u{i}"))
        name, _, per_unit, is_metric = UNITS[index]
        (metric if is_metric else us).append((name, to_number(match.group(1)) * per_unit))
    amounts = metric or us
    if not amounts:
        raise CannotParse("no amount with a unit")
    return Volume(
        ml=sum(ml for _, ml in amounts),
        units=tuple(name for name, _ in amounts),
        all_units=tuple(name for name, _ in metric + us),
    )


def show_ml(ml: Decimal) -> str:
    return format(ml.quantize(Decimal("0.1")).normalize(), "f") + " mL"


def check_net_contents(application: str, label: FieldReading) -> Check:
    said = tidy(application)
    if is_missing(label):
        return Check(Status.FAIL, "The label doesn't show the net contents.")
    shown = tidy(label.text or "")
    if not said:
        return Check(
            Status.REVIEW,
            f'The application leaves the net contents blank. The label says "{shown}".',
        )
    if is_unclear(label):
        return Check(
            Status.REVIEW,
            "Part of the net contents is hard to read on the label. Please check it by eye.",
        )
    try:
        on_label = parse_volume(shown)
    except CannotParse:
        return Check(
            Status.REVIEW,
            f"Couldn't find an amount with a unit in the label's \"{shown}\". "
            "Please check it by eye.",
        )
    try:
        on_application = parse_volume(said)
    except CannotParse:
        return Check(
            Status.REVIEW,
            f"Couldn't find an amount with a unit in the application's \"{said}\". "
            "Please check it by eye.",
        )

    same_units = on_label.units == on_application.units
    larger = max(on_label.ml, on_application.ml)
    if abs(on_label.ml - on_application.ml) > TOLERANCE * larger:
        converted = (
            "" if same_units else f" ({show_ml(on_label.ml)} vs {show_ml(on_application.ml)})"
        )
        return Check(
            Status.FAIL,
            f'The label says "{shown}" but the application says "{said}".{converted}',
        )
    if same_units:
        return Check(Status.PASS, "The net contents match the application.")
    return Check(
        Status.PASS,
        f'The label says "{shown}" and the application says "{said}". '
        "They are the same amount in different units.",
        note=f"Matches, different units ({shown} = {said})",
    )
