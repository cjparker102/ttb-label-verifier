"""The government health warning statement and its checks."""

import re
from difflib import SequenceMatcher

from app.reading.schema import BoldLook, WarningReading
from app.reading.words import Passes
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


def tokens(text: str) -> list[str]:
    """Runs of letters and digits: "(1)According," gives "1" and "According"."""
    return re.findall(r"[^\W_]+", text)


ALIKE = 0.8  # how much of the warning a second reading must have read to count
IN_A_ROW = 3  # words in a row that place the warning on a page without its heading


def warning_start(found: list[str], keys: list[str]) -> int | None:
    """Where the warning starts among a page's words (both in lower case): at its heading,
    or, if Tesseract read no heading (a misspelt or misread "GOVERNMENT"), where the AI
    reader's warning words begin on the page, placed by a run of at least IN_A_ROW of them."""
    for i in range(len(keys) - 1):
        if keys[i] == "government" and keys[i + 1].startswith("warning"):
            return i
    matcher = SequenceMatcher(a=found, b=keys, autojunk=False)
    runs = [block for block in matcher.get_matching_blocks() if block.size >= IN_A_ROW]
    if not runs:
        return None
    return max(0, runs[0].b - runs[0].a)


def differences(found: list[str], page: list[str]) -> dict[tuple[int, int, str], str] | None:
    """Where a page of Tesseract's words differs from the AI reader's warning, word by
    word, ignoring capitals, punctuation, and spacing. Each difference is keyed by the
    AI reader's words it covers and Tesseract's words in their place. None if Tesseract
    didn't read this warning: it isn't on the page, or too little of it is alike."""
    keys = [word.casefold() for word in page]
    start = warning_start([word.casefold() for word in found], keys)
    if start is None:
        return None
    window = page[start : start + len(found) + 8]
    a, b = [word.casefold() for word in found], [word.casefold() for word in window]
    matcher = SequenceMatcher(a=a, b=b, autojunk=False)
    if sum(block.size for block in matcher.get_matching_blocks()) < ALIKE * len(a):
        return None
    result = {}
    for op, i1, i2, j1, j2 in matcher.get_opcodes():
        if op == "equal" or i1 == len(a) or (op == "delete" and j1 == len(b)):
            continue  # past the end of the warning, or of what Tesseract read
        if "".join(a[i1:i2]) == "".join(b[j1:j2]):
            continue  # only spacing differs
        if any(c.isdigit() for c in "".join(b[j1:j2])) and not any(
            c.isdigit() for c in "".join(a[i1:i2])
        ):
            continue  # Tesseract reading letters as digits, "10" for "TO": not a misprint
        result[(i1, i2, "".join(b[j1:j2]))] = " ".join(window[j1:j2])
    return result


def check_second_reading(label: WarningReading, ocr: Passes | None) -> Check | None:
    """The AI reader can read a warning as it should be rather than as printed: a
    misspelt word read as spelt correctly. Tesseract, a second reader, doesn't know
    the warning. Its two passes read the picture separately; where both read a word
    differently from the AI reader, the same way, a person should look. A difference
    only one pass sees is taken for Tesseract misreading small print."""
    if ocr is None or is_missing(label) or label.image_number is None:
        return None
    if not 0 < label.image_number <= len(ocr):
        return None
    found = tokens(tidy(label.text or ""))
    pages = [tokens(" ".join(word.text for word in words)) for words in ocr[label.image_number - 1]]
    readings = [r for r in (differences(found, page) for page in pages) if r is not None]
    if len(readings) < len(pages):
        return None  # a pass didn't read the warning, so they can't confirm each other
    agreed = sorted(set.intersection(*(set(r) for r in readings)))
    if not agreed:
        return Check(
            Status.PASS,
            "A second reading of the warning, by basic text reading, found the same words.",
            citation=WARNING_TEXT_RULE,
        )
    i1, i2, _ = agreed[0]
    ai = " ".join(found[i1:i2]) or "nothing"
    other = readings[0][agreed[0]] or "nothing"
    more = len(agreed) - 1
    extra = f" There {'is' if more == 1 else 'are'} {more} more." if more else ""
    return Check(
        Status.REVIEW,
        f'Two readings of the warning disagree: the AI reader read "{ai}", and basic text '
        f'reading read "{other}".{extra} Please check it by eye.',
        citation=WARNING_TEXT_RULE,
    )


def check_warning(label: WarningReading, ocr: Passes | None = None) -> list[Check]:
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
    second = check_second_reading(label, ocr)
    if second:
        checks.append(second)
    checks += check_bold(label)
    return checks
