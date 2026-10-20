"""Matching rules for the alcohol content statement."""

import re
from dataclasses import dataclass
from decimal import Decimal

from app.reading.schema import FieldReading
from app.rules.results import Check, Status
from app.rules.text import is_missing, is_unclear, tidy

PERCENT = re.compile(r"(\d+(?:[.,]\d+)?)\s*(?:%|percent\b|per\s+cent\b)", re.IGNORECASE)
PROOF = re.compile(r"(\d+(?:[.,]\d+)?)\s*°?\s*proof\b", re.IGNORECASE)
BARE_NUMBER = re.compile(r"^\s*(\d+(?:[.,]\d+)?)\s*$")
# A range such as "11-14%" or "11 to 14 percent": never one number.
RANGE = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*%?\s*(?:-|–|—|to)\s*(\d+(?:[.,]\d+)?)\s*(?:%|percent\b)",
    re.IGNORECASE,
)

# Label and application should state the same number, so only rounding is allowed.
# TTB's tolerances (27 CFR 5.65, 4.36, 7.65) compare the label with the lab-tested
# liquid, not with the application, so they don't apply here.
ABV_TOLERANCE = Decimal("0.05")
# Proof is often rounded to a whole number, so it may be up to half a proof off.
PROOF_TOLERANCE = Decimal("0.5")


class CannotParse(ValueError):
    """The statement has no usable number, or more than one."""


class AlcoholRange(CannotParse):
    """The statement gives a range, such as "11-14%", not one figure."""

    def __init__(self, low: Decimal, high: Decimal):
        super().__init__(f"a range from {low} to {high}")
        self.low, self.high = low, high


@dataclass(frozen=True)
class AlcoholStatement:
    abv: Decimal | None
    proof: Decimal | None

    @property
    def effective_abv(self) -> Decimal:
        """The ABV, worked out from the proof (US proof = 2 x ABV) if only proof is given."""
        if self.abv is not None:
            return self.abv
        assert self.proof is not None
        return self.proof / 2


def to_number(text: str) -> Decimal:
    return Decimal(text.replace(",", "."))


def show(number: Decimal) -> str:
    return format(number.normalize(), "f")


def parse_alcohol(text: str) -> AlcoholStatement:
    for low, high in RANGE.findall(text):
        low_number, high_number = to_number(low), to_number(high)
        if low_number < high_number <= 100:  # not a year or a size before a percentage
            raise AlcoholRange(low_number, high_number)
    percents = {to_number(n) for n in PERCENT.findall(text)}
    proofs = {to_number(n) for n in PROOF.findall(text)}
    if len(percents) > 1 or len(proofs) > 1:
        raise CannotParse("more than one alcohol figure")
    if percents or proofs:
        return AlcoholStatement(abv=next(iter(percents), None), proof=next(iter(proofs), None))
    bare = BARE_NUMBER.match(text)
    if bare:
        return AlcoholStatement(abv=to_number(bare.group(1)), proof=None)
    raise CannotParse("no alcohol figure")


def check_alcohol(application: str, label: FieldReading, optional_on_label: bool = False) -> Check:
    """Compare the alcohol content. `optional_on_label` is set when TTB rules let
    this product's label leave the alcohol content out."""
    said = tidy(application)
    if is_missing(label):
        if not said:
            return Check(
                Status.NOT_NEEDED,
                "Neither the application nor the label states the alcohol content.",
            )
        if optional_on_label:
            # Legal to leave out, but the application states one, so it may be printed
            # where the AI reader missed it: a person should look.
            return Check(
                Status.REVIEW,
                f'The application says "{said}", but no alcohol content was found on the label. '
                "This label may leave it out. Please check.",
            )
        return Check(
            Status.FAIL,
            f'The label doesn\'t show the alcohol content. The application says "{said}".',
        )
    shown = tidy(label.text or "")
    if is_unclear(label):
        return Check(
            Status.REVIEW,
            "Part of the alcohol content is hard to read on the label. Please check it by eye.",
        )
    try:
        on_label = parse_alcohol(shown)
    except AlcoholRange as found:
        return Check(
            Status.REVIEW,
            f"The label gives a range of alcohol content, from {show(found.low)}% to "
            f'{show(found.high)}%, not one figure ("{shown}"). Please check it by eye.',
        )
    except CannotParse:
        return Check(
            Status.REVIEW,
            f"Couldn't find one clear alcohol figure in the label's statement \"{shown}\". "
            "Please check it by eye.",
        )

    if on_label.abv is not None and on_label.proof is not None:
        if abs(on_label.proof - 2 * on_label.abv) > PROOF_TOLERANCE:
            return Check(
                Status.FAIL,
                f"The label says {show(on_label.abv)}% alcohol but {show(on_label.proof)} proof. "
                f"{show(on_label.abv)}% alcohol is {show(2 * on_label.abv)} proof.",
            )

    if not said:
        return Check(
            Status.REVIEW,
            f'The application leaves the alcohol content blank. The label says "{shown}".',
        )
    try:
        on_application = parse_alcohol(said)
    except CannotParse:
        return Check(
            Status.REVIEW,
            f"Couldn't find one clear alcohol figure in the application's \"{said}\". "
            "Please check it by eye.",
        )

    label_abv, application_abv = on_label.effective_abv, on_application.effective_abv
    if abs(label_abv - application_abv) > ABV_TOLERANCE:
        return Check(
            Status.FAIL,
            f"The label says {show(label_abv)}% but the application says {show(application_abv)}%.",
        )
    if on_label.proof is not None and on_application.proof is not None:
        if abs(on_label.proof - on_application.proof) > PROOF_TOLERANCE:
            return Check(
                Status.FAIL,
                f"The label says {show(on_label.proof)} proof but the application says "
                f"{show(on_application.proof)} proof.",
            )
    return Check(Status.PASS, "The alcohol content matches the application.")


def check_alcohol_statements(statements: list[str]) -> Check | None:
    """A label can state its alcohol content more than once, on different pictures. If
    the statements disagree, as a front saying 13% and a back saying 11-14%, a person must
    look. Statements without a figure are left out; None if nothing disagrees."""
    found: dict[object, str] = {}
    for statement in statements:
        try:
            value: object = parse_alcohol(tidy(statement)).effective_abv
        except AlcoholRange as found_range:
            value = (found_range.low, found_range.high)
        except CannotParse:
            continue
        if not any(same_alcohol(value, other) for other in found):
            found[value] = tidy(statement)
    if len(found) < 2:
        return None
    listed = " and ".join(f'"{text}"' for text in found.values())
    return Check(
        Status.REVIEW,
        f"The label states its alcohol content more than once, and the statements disagree: "
        f"{listed}. Please check it by eye.",
    )


def same_alcohol(a: object, b: object) -> bool:
    if isinstance(a, Decimal) and isinstance(b, Decimal):
        return abs(a - b) <= ABV_TOLERANCE
    return a == b
