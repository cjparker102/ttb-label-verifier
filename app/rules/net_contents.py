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


Amounts = tuple[tuple[str, Decimal], ...]  # (unit name, milliliters) for each amount


@dataclass(frozen=True)
class Volume:
    metric: Amounts
    us: Amounts

    def counted(self, prefer_us: bool = False) -> Amounts:
        """The amounts that count. When a label gives both systems, metric counts,
        unless asked for US units and the label has them."""
        if (prefer_us and self.us) or not self.metric:
            return self.us
        return self.metric

    @property
    def ml(self) -> Decimal:
        return sum((ml for _, ml in self.counted()), Decimal(0))

    @property
    def units(self) -> tuple[str, ...]:
        return tuple(name for name, _ in self.counted())

    @property
    def all_units(self) -> tuple[str, ...]:
        return tuple(name for name, _ in self.metric + self.us)

    def like(self, other: "Volume") -> tuple[Decimal, tuple[str, ...]]:
        """This volume measured the way `other` was written: in US units if `other`
        used only US units and this volume has them, otherwise as usual."""
        amounts = self.counted(prefer_us=not other.metric)
        return sum((ml for _, ml in amounts), Decimal(0)), tuple(name for name, _ in amounts)


def to_number(text: str) -> Decimal:
    if THOUSANDS.match(text):
        return Decimal(text.replace(",", ""))
    return Decimal(text.replace(",", "."))


def parse_volume(text: str) -> Volume:
    """The metric and US amounts in a net contents statement, in mL."""
    metric: list[tuple[str, Decimal]] = []
    us: list[tuple[str, Decimal]] = []
    for match in AMOUNT.finditer(text.replace("℮", " ")):
        index = next(i for i in range(len(UNITS)) if match.group(f"u{i}"))
        name, _, per_unit, is_metric = UNITS[index]
        (metric if is_metric else us).append((name, to_number(match.group(1)) * per_unit))
    if not metric and not us:
        raise CannotParse("no amount with a unit")
    return Volume(metric=tuple(metric), us=tuple(us))


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

    # "16.9 FL. OZ. (500 mL)" is compared in fluid ounces with an application that says
    # "16.9 fl oz", and in milliliters with one that says "500 mL".
    label_ml, label_units = on_label.like(on_application)
    same_units = label_units == on_application.units
    larger = max(label_ml, on_application.ml)
    if abs(label_ml - on_application.ml) > TOLERANCE * larger:
        converted = "" if same_units else f" ({show_ml(label_ml)} vs {show_ml(on_application.ml)})"
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
