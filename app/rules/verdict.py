"""Runs every rule on one label and combines the results."""

from collections import Counter
from dataclasses import dataclass

from app.reading.schema import LabelReading
from app.reading.strokes import HeadingWeight
from app.reading.words import Passes
from app.rules.alcohol import check_alcohol, check_alcohol_statements
from app.rules.application import Application
from app.rules.countries import check_country
from app.rules.names import check_bottler, check_brand, check_class, class_elsewhere
from app.rules.net_contents import check_net_contents, check_net_contents_statements
from app.rules.results import Check, Status, worst
from app.rules.ttb import alcohol_may_be_left_out, ttb_checks
from app.rules.warning import GOVERNMENT_WARNING, check_warning, heading_elsewhere


@dataclass(frozen=True)
class FieldResult:
    field: str  # the LabelReading field name
    title: str  # the name shown to agents
    application_says: str
    label_says: str | None
    image_number: int | None
    checks: tuple[Check, ...]

    @property
    def status(self) -> Status:
        return worst(check.status for check in self.checks)

    @property
    def notes(self) -> list[str]:
        return [check.note for check in self.checks if check.note]


@dataclass(frozen=True)
class LabelResult:
    fields: tuple[FieldResult, ...]

    @property
    def status(self) -> Status:
        return worst(field.status for field in self.fields)

    @property
    def counts(self) -> Counter:
        return Counter(field.status for field in self.fields)


def also(check: Check | None) -> list[Check]:
    return [check] if check else []


def check_label(
    application: Application,
    reading: LabelReading,
    ocr: Passes | None = None,
    heading: HeadingWeight | None = None,
) -> LabelResult:
    """Match checks first, then the TTB rule checks for the same field. `ocr` is a
    second reading of the label by Tesseract, if there is one, and `heading` the warning
    heading's strokes measured from it, if they could be."""
    class_check = check_class(application.class_type, reading.class_type)
    if class_check.status == Status.FAIL:
        # The application's class found elsewhere on the label is preferred over what the
        # AI reader took for the class, such as a fanciful name, for every rule.
        found = class_elsewhere(application.class_type, reading.class_type, ocr)
        if found:
            class_check, class_type = found
            reading = reading.model_copy(update={"class_type": class_type})
    rules = ttb_checks(application, reading)

    def field(name: str, title: str, said: str, checks: list[Check]) -> FieldResult:
        label = getattr(reading, name)
        checks = checks + rules.get(name, [])
        return FieldResult(name, title, said, label.text, label.image_number, tuple(checks))

    a, r = application, reading
    alcohol_optional = alcohol_may_be_left_out(a.beverage_type, r)
    return LabelResult(
        (
            field(
                "brand_name",
                "Brand name",
                a.brand_name,
                [check_brand(a.brand_name, r, ocr)],
            ),
            field(
                "class_type",
                "Class / type",
                a.class_type,
                [class_check],
            ),
            field(
                "alcohol_content",
                "Alcohol content",
                a.alcohol_content,
                [check_alcohol(a.alcohol_content, r.alcohol_content, alcohol_optional)]
                + also(check_alcohol_statements(r.alcohol_statements)),
            ),
            field(
                "net_contents",
                "Net contents",
                a.net_contents,
                [check_net_contents(a.net_contents, r.net_contents)]
                + also(check_net_contents_statements(r.net_contents_statements)),
            ),
            field(
                "bottler_name_address",
                "Bottler name and address",
                a.bottler_name_address,
                [check_bottler(a.bottler_name_address, r.bottler_name_address)],
            ),
            field(
                "country_of_origin",
                "Country of origin",
                a.country_of_origin,
                [check_country(a.country_of_origin, r.country_of_origin, r.bottler_name_address)],
            ),
            field(
                "government_warning",
                "Government warning",
                GOVERNMENT_WARNING,
                check_warning(r.government_warning, ocr, heading_elsewhere(r, ocr), heading),
            ),
        )
    )
