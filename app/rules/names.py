"""Matching rules for names: brand name, class/type, and bottler name and address."""

import re
from dataclasses import replace

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


# Words that say what a company did, before "by" or "for": "Distilled and bottled by",
# "Imported by", "Bottled for". Only these start a new statement in a bottler field.
ACTIONS = {
    "aged", "blended", "bottled", "brewed", "canned", "cellared", "crafted", "distilled",
    "distributed", "estate", "fermented", "finished", "grown", "imported", "kegged", "made",
    "manufactured", "packaged", "packed", "prepared", "produced", "rectified", "vinted",
}  # fmt: skip
JOINERS = {"and", "&"}


def bare(word: str) -> str:
    return "".join(c for c in word.casefold() if c.isalnum() or c == "&")


def statements(text: str) -> list[str]:
    """A bottler field split into its statements. Labels often carry more than one,
    such as "Distilled by ..." and "Bottled by ...", or a French "Mis en bouteille au
    château" next to "Imported by ...". A statement starts at the words saying what a
    company did, just before "by" or "for", so "by" or "for" inside a company name
    never starts one."""
    words = tidy(text).split()
    starts = {0}
    for i, word in enumerate(words):
        if bare(word) not in ("by", "for"):
            continue
        start, j = i, i - 1
        while j >= 0:
            if bare(words[j]) in ACTIONS:
                start = j
            elif not (bare(words[j]) in JOINERS and j > 0 and bare(words[j - 1]) in ACTIONS):
                break
            j -= 1
        if start < i:
            starts.add(start)
    bounds = sorted(starts) + [len(words)]
    parts = []
    for a, b in zip(bounds, bounds[1:], strict=False):
        part = words[a:b]
        while part and bare(part[-1]) in JOINERS:
            part = part[:-1]  # "..., Kentucky and" before "bottled for ..."
        if part:
            parts.append(" ".join(part))
    return parts


def role(statement: str) -> set[str]:
    """What the company did, from the words before "by" or "for": {"bottled"} for
    "Bottled by ...". Empty if the statement doesn't say."""
    match = LEAD_IN.match(tidy(statement))
    return {bare(word) for word in match.group(0).split()} & ACTIONS if match else set()


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
    # The label may name several companies, such as a distiller and a bottler. One of
    # them can match, but only in the role the application gives it, if it gives one.
    parts = statements(label.text or "")
    if len(parts) > 1:
        wanted = role(application)
        for part in parts:
            if not wanted <= role(part):
                continue
            part_result = compare_names(what, said, strip_lead_in(part))
            if part_result.status == Status.PASS:
                others = "; ".join(p for p in parts if p is not part)
                return replace(
                    part_result, reason=f'{part_result.reason} The label also says "{others}".'
                )
    result = compare_names(what, said, shown)
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
