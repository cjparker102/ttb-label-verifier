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
    ("gallon", r"gallons?|gals?\.?", Decimal("3785.411784"), False),
]
AMOUNT = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*(?:U\.?S\.?\s+)?(?:"  # "5.16 US GALS"
    + "|".join(f"(?P<u{i}>{pattern})" for i, (_, pattern, _, _) in enumerate(UNITS))
    + r")(?![a-z])",
    re.IGNORECASE,
)
THOUSANDS = re.compile(r"^[1-9]\d{0,2},\d{3}$")  # 1,750 is one thousand seven hundred fifty

# Converting between units rounds, so allow half a percent.
TOLERANCE = Decimal("0.005")
# A label's metric and US amounts are rounded separately ("500 mL (17 fl oz)" is 0.5% off,
# "200 mL (6.8 fl oz)" 0.6%), so they count as the same amount within 2%.
SYSTEMS_AGREE = Decimal("0.02")


class CannotParse(ValueError):
    """The statement has no amount with a known unit."""


Amounts = tuple[tuple[str, Decimal], ...]  # (unit name, milliliters) for each amount


@dataclass(frozen=True)
class Volume:
    metric: Amounts
    us: Amounts
    # When a label lists different sizes, as keg labels with a box to tick for each do,
    # the sizes in each system, in mL. Empty for one amount.
    metric_sizes: tuple[Decimal, ...] = ()
    us_sizes: tuple[Decimal, ...] = ()

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

    @property
    def sizes(self) -> tuple[Decimal, ...]:
        """Every size the label lists, in the system that counts."""
        listed = self.us_sizes if self.counted() is self.us else self.metric_sizes
        return listed or (self.ml,)

    def sizes_like(self, other: "Volume") -> tuple[Decimal, ...]:
        """The different sizes listed, in the system `like` uses. Empty for one amount."""
        return (
            self.us_sizes
            if self.counted(prefer_us=not other.metric) is self.us
            else (self.metric_sizes)
        )

    def like(self, other: "Volume") -> tuple[Decimal, tuple[str, ...]]:
        """This volume measured the way `other` was written: in US units if `other`
        used only US units and this volume has them, otherwise as usual."""
        amounts = self.counted(prefer_us=not other.metric)
        return sum((ml for _, ml in amounts), Decimal(0)), tuple(name for name, _ in amounts)


def to_number(text: str) -> Decimal:
    if THOUSANDS.match(text):
        return Decimal(text.replace(",", ""))
    return Decimal(text.replace(",", "."))


def close(a: Decimal, b: Decimal) -> bool:
    return abs(a - b) <= TOLERANCE * max(a, b)


def one_amount(amounts: list[tuple[str, Decimal, Decimal]]) -> tuple[Amounts, tuple[Decimal, ...]]:
    """Amounts in one system, as (unit name, mL, mL per unit), read as one statement.
    Falling units add up when each part is less than one of the unit before it, as in
    "1 pint 9 fl oz". The same amount given twice, in the same unit or not, counts once:
    "1L ... 1 liter", "1 PINT (16 FL OZ)". Different sizes are a list to choose from: the
    first is returned as the amount, and all of them as the sizes."""
    pairs = list(zip(amounts, amounts[1:], strict=False))
    adds_up = all(a[2] > b[2] and b[1] < a[2] * (1 - TOLERANCE) for a, b in pairs)
    if len(amounts) <= 1 or adds_up:
        return tuple((name, ml) for name, ml, _ in amounts), ()
    sizes: list[Decimal] = []
    for _, ml, _ in amounts:
        if not any(close(ml, size) for size in sizes):
            sizes.append(ml)
    name, ml, _ = amounts[0]
    return ((name, ml),), tuple(sizes) if len(sizes) > 1 else ()


def parse_volume(text: str) -> Volume:
    """The metric and US amounts in a net contents statement, in mL."""
    metric: list[tuple[str, Decimal, Decimal]] = []
    us: list[tuple[str, Decimal, Decimal]] = []
    for match in AMOUNT.finditer(text.replace("℮", " ")):
        index = next(i for i in range(len(UNITS)) if match.group(f"u{i}"))
        name, _, per_unit, is_metric = UNITS[index]
        amount = (name, to_number(match.group(1)) * per_unit, per_unit)
        (metric if is_metric else us).append(amount)
    if not metric and not us:
        raise CannotParse("no amount with a unit")
    metric_amounts, metric_sizes = one_amount(metric)
    us_amounts, us_sizes = one_amount(us)
    return Volume(metric_amounts, us_amounts, metric_sizes, us_sizes)


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

    sizes = on_label.sizes_like(on_application)
    if sizes:
        if any(close(size, on_application.ml) for size in sizes):
            return Check(
                Status.REVIEW,
                f'The label lists several sizes, "{shown}", and one of them is the '
                f'application\'s "{said}". Please check which one the label marks.',
            )
        return Check(
            Status.FAIL,
            f'The label lists several sizes, "{shown}", and none of them is the '
            f'application\'s "{said}".',
        )

    # A label giving both systems must give the same amount in each. If they disagree, as in
    # "750 mL (12 fl oz)", a person must look, unless the application matches neither.
    if on_label.metric and on_label.us:
        metric_ml = sum((ml for _, ml in on_label.metric), Decimal(0))
        us_ml = sum((ml for _, ml in on_label.us), Decimal(0))
        if abs(metric_ml - us_ml) > SYSTEMS_AGREE * max(metric_ml, us_ml):
            if any(close(ml, on_application.ml) for ml in (metric_ml, us_ml)):
                return Check(
                    Status.REVIEW,
                    f'The label\'s metric and US amounts disagree: "{shown}" is '
                    f"{show_ml(metric_ml)} in metric units but {show_ml(us_ml)} in US units. "
                    "Please check it by eye.",
                )
            return Check(
                Status.FAIL,
                f'The label says "{shown}" but the application says "{said}". The label\'s '
                f"metric and US amounts also disagree ({show_ml(metric_ml)} and "
                f"{show_ml(us_ml)}).",
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


def check_net_contents_statements(statements: list[str]) -> Check | None:
    """A label can state its net contents more than once, on different pictures. If the
    statements give different amounts, as a front saying 75 ml and a back saying 750 ml, a
    person must look. The same amount in other units ("750 mL" and "25.4 FL OZ") agrees.
    Statements without an amount, or listing several sizes, are left out."""
    found: list[tuple[Decimal, str]] = []
    for statement in statements:
        try:
            volume = parse_volume(tidy(statement))
        except CannotParse:
            continue
        if volume.metric_sizes or volume.us_sizes:
            continue
        ml = volume.ml
        if not any(abs(ml - other) <= SYSTEMS_AGREE * max(ml, other) for other, _ in found):
            found.append((ml, tidy(statement)))
    if len(found) < 2:
        return None
    listed = " and ".join(f'"{text}"' for _, text in found)
    return Check(
        Status.REVIEW,
        f"The label states its net contents more than once, and the amounts differ: {listed}. "
        "Please check it by eye.",
    )
