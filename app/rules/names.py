"""Matching rules for names: brand name, class/type, and bottler name and address."""

import re

from app.reading.schema import FieldReading
from app.rules.results import Check, Status
from app.rules.text import (
    cosmetic_differences,
    is_missing,
    is_unclear,
    join_words,
    loose_key,
    non_latin_script,
    tidy,
    without_accents,
)

# Words such as "Bottled by", "Distilled and bottled by", "Imported by", or
# "Bottled for" at the start.
LEAD_IN = re.compile(r"^\s*(?:[^\W\d_]+[\s,&]+){1,6}?(?:by|for)\b\s*:?\s*", re.IGNORECASE)


def check_name(what: str, application: str, label: FieldReading) -> Check:
    """Compare a name on the label with the application.

    `what` names the field in messages, for example "brand name".
    """
    if is_missing(label):
        return Check(Status.FAIL, f"The label doesn't show the {what}.")
    said, shown = tidy(application), tidy(label.text or "")
    if not said:
        return Check(
            Status.REVIEW, f'The application leaves the {what} blank. The label says "{shown}".'
        )
    if is_unclear(label):
        return Check(
            Status.REVIEW,
            f"Part of the {what} is hard to read on the label. Please check it by eye.",
        )
    return compare_names(what, said, shown)


def compare_names(what: str, said: str, shown: str) -> Check:
    both = f'The label says "{shown}" and the application says "{said}".'
    if said == shown:
        return Check(Status.PASS, f"The {what} matches the application.")
    if loose_key(said) == loose_key(shown):
        differences = join_words(cosmetic_differences(said, shown))
        return Check(
            Status.PASS,
            f"{both} Only the {differences} differ.",
            note=f"Matches, different {differences}",
        )
    if loose_key(without_accents(said)) == loose_key(without_accents(shown)):
        return Check(Status.REVIEW, f"{both} The accents differ. Please check.")
    label_script = non_latin_script(shown)
    if label_script and not non_latin_script(said):
        return Check(
            Status.REVIEW,
            f'The label shows the {what} in {label_script} script ("{shown}") and the '
            f'application uses a romanized spelling ("{said}"). Please check by eye.',
        )
    return Check(Status.FAIL, f'The label says "{shown}" but the application says "{said}".')


def strip_lead_in(text: str) -> str:
    return LEAD_IN.sub("", tidy(text), count=1)


def statements(text: str) -> list[str]:
    """A bottler field split into its statements. Labels often carry more than one,
    such as "Distilled by ..." and "Bottled by ...", or a French "Mis en bouteille au
    château" next to "Imported by ...". A statement starts at the nearest capitalized
    word within three words before "by" or "for"."""
    words = tidy(text).split()
    starts = {0}
    for i, word in enumerate(words):
        if word.casefold() in ("by", "for", "by:", "for:"):
            capitalized = [j for j in range(max(0, i - 3), i) if words[j][:1].isupper()]
            if capitalized:
                starts.add(capitalized[-1])
    bounds = sorted(starts) + [len(words)]
    return [" ".join(words[a:b]) for a, b in zip(bounds, bounds[1:], strict=False) if a < b]


def check_bottler(application: str, label: FieldReading) -> Check:
    """Compare the bottler or importer name and address, ignoring words like "Bottled by"."""
    what = "bottler name and address"
    if is_missing(label):
        return Check(Status.FAIL, f"The label doesn't show the {what}.")
    said, shown = strip_lead_in(application), strip_lead_in(label.text or "")
    if not said:
        return Check(
            Status.REVIEW, f'The application leaves the {what} blank. The label says "{shown}".'
        )
    if is_unclear(label):
        return Check(
            Status.REVIEW,
            f"Part of the {what} is hard to read on the label. Please check it by eye.",
        )
    result = compare_names(what, said, shown)
    if result.status == Status.PASS:
        return result
    parts = statements(label.text or "")
    if len(parts) > 1:
        for part in parts:
            part_result = compare_names(what, said, strip_lead_in(part))
            if part_result.status == Status.PASS:
                return part_result
    if result.status != Status.FAIL:
        return result
    said_name, shown_name = said.split(",")[0], shown.split(",")[0]
    if loose_key(said_name) == loose_key(shown_name):
        return Check(
            Status.REVIEW,
            f'Same company name, but the address is written differently. The label says "{shown}" '
            f'and the application says "{said}".',
        )
    return result
