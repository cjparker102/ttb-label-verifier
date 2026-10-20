"""The government health warning statement and its checks."""

import re
from difflib import SequenceMatcher

from app.reading.schema import BoldLook, WarningReading
from app.rules.citations import WARNING_FORMAT as WARNING_FORMAT_RULE
from app.rules.citations import WARNING_TEXT as WARNING_TEXT_RULE
from app.rules.results import Check, Status, WordChange
from app.rules.text import is_missing, is_unclear, tidy

# 27 CFR 16.21, https://www.ecfr.gov/current/title-27/section-16.21
# Checked character for character against the eCFR XML on Oct 19, 2026
# (Title 27 up to date as of Oct 15, 2026). The regulation prints the two
# numbered sentences as separate paragraphs; here they are joined by one space.
GOVERNMENT_WARNING = (
    "GOVERNMENT WARNING: (1) According to the Surgeon General, women should not drink "
    "alcoholic beverages during pregnancy because of the risk of birth defects. "
    "(2) Consumption of alcoholic beverages impairs your ability to drive a car or "
    "operate machinery, and may cause health problems."
)

# 16.22(a)(2): "The first two words of the statement required by § 16.21, i.e.,
# "GOVERNMENT WARNING," shall appear in capital letters and in bold type. The
# remainder of the warning statement may not appear in bold type."
HEADING = "GOVERNMENT WARNING"
HEADING_ANYWHERE = re.compile(r"government\s+warning", re.IGNORECASE)


def word_changes(required: str, found: str) -> list[WordChange]:
    """Word-by-word differences. Capitals don't matter here; the heading's capitals
    are checked on their own."""
    required_words, found_words = required.split(), found.split()
    matcher = SequenceMatcher(
        a=[w.casefold() for w in required_words],
        b=[w.casefold() for w in found_words],
        autojunk=False,
    )
    kinds = {"delete": "missing", "insert": "extra", "replace": "changed"}
    return [
        WordChange(kinds[op], " ".join(required_words[i1:i2]), " ".join(found_words[j1:j2]))
        for op, i1, i2, j1, j2 in matcher.get_opcodes()
        if op != "equal"
    ]


def track_changes(required: str, found: str) -> list[tuple[str, str]]:
    """The whole statement as runs of ("same" | "missing" | "extra", words), for a
    track-changes view. Like word_changes, capitals don't count as differences."""
    required_words, found_words = required.split(), found.split()
    matcher = SequenceMatcher(
        a=[w.casefold() for w in required_words],
        b=[w.casefold() for w in found_words],
        autojunk=False,
    )
    runs = []
    for op, i1, i2, j1, j2 in matcher.get_opcodes():
        if op == "equal":
            runs.append(("same", " ".join(found_words[j1:j2])))
            continue
        if i2 > i1:
            runs.append(("missing", " ".join(required_words[i1:i2])))
        if j2 > j1:
            runs.append(("extra", " ".join(found_words[j1:j2])))
    return runs


def describe(change: WordChange) -> str:
    if change.kind == "missing":
        return f'"{change.required}" is missing'
    if change.kind == "extra":
        return f'"{change.found}" was added'
    return f'"{change.required}" was changed to "{change.found}"'


def letters_and_numbers(text: str) -> str:
    return "".join(ch for ch in text.casefold() if ch.isalnum())


def check_wording(text: str, unclear: bool) -> Check:
    changes = word_changes(GOVERNMENT_WARNING, text)
    if not changes:
        if unclear:
            return Check(
                Status.REVIEW,
                "Part of the warning is hard to read on the label. Please check it by eye.",
                citation=WARNING_TEXT_RULE,
            )
        return Check(
            Status.PASS,
            "The warning wording matches the required text.",
            citation=WARNING_TEXT_RULE,
        )
    if unclear:
        return Check(
            Status.REVIEW,
            "Part of the warning is hard to read on the label, and it may differ from the "
            "required text. Please check it by eye.",
            citation=WARNING_TEXT_RULE,
            changes=tuple(changes),
        )
    more = len(changes) - 1
    extra = (
        f" There {'is' if more == 1 else 'are'} {more} more difference{'s' * (more != 1)}."
        if more
        else ""
    )
    # Every word right, but a comma, period, parenthesis, or space differs. TTB approves
    # such labels and asks for a fix on the next print run, so a person should look,
    # but it isn't called a Problem. A changed or misspelt word still is.
    if letters_and_numbers(text) == letters_and_numbers(GOVERNMENT_WARNING):
        return Check(
            Status.REVIEW,
            "Only the punctuation or spacing of the warning differs from the required text: "
            f"{describe(changes[0])}.{extra} Please check it.",
            citation=WARNING_TEXT_RULE,
            changes=tuple(changes),
        )
    return Check(
        Status.FAIL,
        f"The warning wording differs from the required text: {describe(changes[0])}.{extra}",
        citation=WARNING_TEXT_RULE,
        changes=tuple(changes),
    )


def check_capitals(text: str) -> Check | None:
    match = HEADING_ANYWHERE.search(text)
    if not match or "[?]" in match.group(0):
        return None  # the wording check already reports a missing heading
    heading = match.group(0)
    if heading.split() == HEADING.split():
        return Check(
            Status.PASS, '"GOVERNMENT WARNING" is in capital letters.', citation=WARNING_FORMAT_RULE
        )
    return Check(
        Status.FAIL,
        f'"GOVERNMENT WARNING" must be in capital letters. The label has "{heading}".',
        citation=WARNING_FORMAT_RULE,
    )


def check_bold(label: WarningReading) -> list[Check]:
    checks = []
    if label.heading_bold == BoldLook.YES:
        checks.append(
            Check(Status.PASS, '"GOVERNMENT WARNING" looks bold.', citation=WARNING_FORMAT_RULE)
        )
    elif label.heading_bold == BoldLook.NO:
        checks.append(
            Check(
                Status.REVIEW,
                '"GOVERNMENT WARNING" doesn\'t look bold on the label, and it must be bold. '
                "Please check it by eye.",
                citation=WARNING_FORMAT_RULE,
            )
        )
    else:
        checks.append(
            Check(
                Status.REVIEW,
                'Can\'t tell from the image whether "GOVERNMENT WARNING" is bold. '
                "Please check it by eye.",
                citation=WARNING_FORMAT_RULE,
            )
        )

    if label.rest_bold == BoldLook.NO:
        checks.append(
            Check(Status.PASS, "The rest of the warning is not bold.", citation=WARNING_FORMAT_RULE)
        )
    elif label.rest_bold == BoldLook.YES:
        checks.append(
            Check(
                Status.REVIEW,
                'The rest of the warning looks bold. Only "GOVERNMENT WARNING" may be bold. '
                "Please check it by eye.",
                citation=WARNING_FORMAT_RULE,
            )
        )
    else:
        checks.append(
            Check(
                Status.REVIEW,
                "Can't tell from the image whether the rest of the warning is bold. "
                "Please check it by eye.",
                citation=WARNING_FORMAT_RULE,
            )
        )
    return checks


def check_warning(label: WarningReading) -> list[Check]:
    if is_missing(label):
        return [
            Check(
                Status.FAIL,
                "The government warning is missing from the label.",
                citation=WARNING_TEXT_RULE,
            )
        ]
    text = tidy(label.text or "")
    checks = [check_wording(text, is_unclear(label))]
    capitals = check_capitals(text)
    if capitals:
        checks.append(capitals)
    checks += check_bold(label)
    return checks
