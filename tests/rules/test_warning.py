import pytest

from app.reading.words import Word
from app.rules.results import Status, WordChange, worst
from app.rules.warning import (
    GOVERNMENT_WARNING,
    WARNING_FORMAT_RULE,
    WARNING_TEXT_RULE,
    check_second_reading,
    check_warning,
)
from tests.rules.helpers import read_warning

BODY = GOVERNMENT_WARNING.removeprefix("GOVERNMENT WARNING: ")


def statuses(checks):
    return [check.status for check in checks]


def test_correct_warning_passes_every_check():
    checks = check_warning(read_warning(GOVERNMENT_WARNING))
    assert statuses(checks) == [Status.PASS] * 4


def test_line_breaks_and_extra_spaces_do_not_matter():
    text = GOVERNMENT_WARNING.replace(" (2) ", "\n(2)  ")
    assert worst(statuses(check_warning(read_warning(text)))) == Status.PASS


def test_body_in_capitals_is_allowed():
    text = "GOVERNMENT WARNING: " + BODY.upper()
    assert worst(statuses(check_warning(read_warning(text)))) == Status.PASS


def test_heading_in_title_case_fails_on_capitals_only():
    checks = check_warning(read_warning("Government Warning: " + BODY))
    wording, capitals = checks[0], checks[1]
    assert wording.status == Status.PASS
    assert capitals.status == Status.FAIL
    assert capitals.reason == (
        '"GOVERNMENT WARNING" must be in capital letters. The label has "Government Warning".'
    )
    assert capitals.citation == WARNING_FORMAT_RULE


@pytest.mark.parametrize(
    ("text", "change", "reason"),
    [
        (
            GOVERNMENT_WARNING.replace("drive a car or", "drive or"),
            WordChange("missing", "a car", ""),
            'The warning wording differs from the required text: "a car" is missing.',
        ),
        (
            GOVERNMENT_WARNING.replace("cause health", "cause serious health"),
            WordChange("extra", "", "serious"),
            'The warning wording differs from the required text: "serious" was added.',
        ),
        (
            GOVERNMENT_WARNING.replace("and may cause", "and can cause"),
            WordChange("changed", "may", "can"),
            'The warning wording differs from the required text: "may" was changed to "can".',
        ),
        (
            GOVERNMENT_WARNING.replace("Surgeon", "Surgeron"),
            WordChange("changed", "Surgeon", "Surgeron"),
            'The warning wording differs from the required text: "Surgeon" was changed to '
            '"Surgeron".',
        ),
    ],
)
def test_wording_differences_fail_and_are_listed(text, change, reason):
    wording = check_warning(read_warning(text))[0]
    assert wording.status == Status.FAIL
    assert wording.changes == (change,)
    assert wording.reason == reason
    assert wording.citation == WARNING_TEXT_RULE


# Approved labels in TTB's Public COLA Registry carry differences like these: TTB approves
# them and asks for the fix when new labels are printed. So they need a look, not a Problem.
@pytest.mark.parametrize(
    ("text", "change"),
    [
        (GOVERNMENT_WARNING.removesuffix("."), WordChange("changed", "problems.", "problems")),
        (
            GOVERNMENT_WARNING.replace("machinery,", "machinery"),
            WordChange("changed", "machinery,", "machinery"),
        ),
        (GOVERNMENT_WARNING.replace("(2)", "2)"), WordChange("changed", "(2)", "2)")),
        (
            GOVERNMENT_WARNING.replace("WARNING:", "WARNING"),
            WordChange("changed", "WARNING:", "WARNING"),
        ),
        (
            GOVERNMENT_WARNING.replace("(1) According", "(1)According"),
            WordChange("changed", "(1) According", "(1)According"),
        ),
    ],
)
def test_punctuation_or_spacing_differences_need_review_not_fail(text, change):
    wording = check_warning(read_warning(text))[0]
    assert wording.status == Status.REVIEW
    assert wording.changes == (change,)
    assert wording.reason.startswith(
        "Only the punctuation or spacing of the warning differs from the required text: "
    )
    assert wording.reason.endswith("Please check it.")
    assert wording.citation == WARNING_TEXT_RULE


def test_a_word_change_with_a_punctuation_difference_still_fails():
    text = GOVERNMENT_WARNING.removesuffix(".").replace("may cause", "can cause")
    assert check_warning(read_warning(text))[0].status == Status.FAIL


def test_several_differences_are_counted():
    text = GOVERNMENT_WARNING.replace("drive a car or", "drive or").replace("may", "can")
    wording = check_warning(read_warning(text))[0]
    assert wording.reason.endswith("There is 1 more difference.")


def test_missing_warning_fails():
    checks = check_warning(read_warning(None))
    assert statuses(checks) == [Status.FAIL]
    assert checks[0].citation == WARNING_TEXT_RULE


@pytest.mark.parametrize(
    ("heading_bold", "rest_bold"),
    [("no", "no"), ("cant_tell", "no"), ("yes", "yes"), ("yes", "cant_tell")],
)
def test_bold_problems_need_review(heading_bold, rest_bold):
    checks = check_warning(read_warning(GOVERNMENT_WARNING, heading_bold, rest_bold))
    assert worst(statuses(checks)) == Status.REVIEW
    assert all(c.citation == WARNING_FORMAT_RULE for c in checks[2:])


def test_hard_to_read_warning_needs_review_not_fail():
    unclear = read_warning(
        GOVERNMENT_WARNING.replace("drive a car", "drive a c[?]r"), readability="unclear"
    )
    checks = check_warning(unclear)
    assert checks[0].status == Status.REVIEW
    assert worst(statuses(checks)) == Status.REVIEW


def test_hard_to_read_warning_needs_review_even_if_it_matches():
    checks = check_warning(read_warning(GOVERNMENT_WARNING, readability="unclear"))
    assert checks[0].status == Status.REVIEW


def test_track_changes_show_the_whole_statement_with_differences_marked():
    from app.rules.warning import track_changes

    found = GOVERNMENT_WARNING.replace("drive a car or", "drive or").replace(
        "may cause", "can cause"
    )
    runs = track_changes(GOVERNMENT_WARNING, found)
    assert ("missing", "a car") in runs
    assert ("missing", "may") in runs and ("extra", "can") in runs
    # Reading only the "same" and "extra" runs gives back the label's own wording.
    assert " ".join(text for kind, text in runs if kind != "missing") == found


def test_track_changes_of_a_correct_warning_is_one_unchanged_run():
    from app.rules.warning import track_changes

    assert track_changes(GOVERNMENT_WARNING, GOVERNMENT_WARNING) == [("same", GOVERNMENT_WARNING)]


# A second reading by Tesseract. The AI reader can read a warning as it should be rather
# than as printed: an approved label in TTB's Public COLA Registry misspells a word in it,
# and Claude read it spelt correctly.


def passes(*texts):
    """Tesseract's passes over picture 1, each given as its text."""
    return [[[Word(word, 0, 0, 10, 10) for word in text.split()] for text in texts]]


MISSPELT = GOVERNMENT_WARNING.replace("pregnancy", "pregnacy")


def second_reading(ocr, text=GOVERNMENT_WARNING):
    return check_second_reading(read_warning(text), ocr)


def test_both_passes_reading_a_word_differently_needs_review():
    result = second_reading(passes(MISSPELT, "Some other text " + MISSPELT))
    assert result.status == Status.REVIEW
    assert result.reason == (
        'Two readings of the warning disagree: the AI reader read "pregnancy", and basic text '
        'reading read "pregnacy". Please check it by eye.'
    )


def test_a_difference_only_one_pass_sees_is_taken_for_a_misreading():
    result = second_reading(passes(MISSPELT, GOVERNMENT_WARNING))
    assert result.status == Status.PASS


def test_both_passes_agreeing_with_the_ai_reader_pass():
    assert second_reading(passes(GOVERNMENT_WARNING, GOVERNMENT_WARNING)).status == Status.PASS


def test_no_claim_when_a_pass_did_not_read_the_warning():
    assert second_reading(passes(MISSPELT, "750 mL 40% Alc./Vol.")) is None
    assert second_reading(passes(MISSPELT, "GOVERNMENT WARNING: unreadable smudge")) is None
    assert second_reading(None) is None


def test_capitals_punctuation_and_spacing_dont_count():
    looks_different = (
        GOVERNMENT_WARNING.upper()
        .replace("(1) ", "(1)")
        .replace("alcoholic beverages", "alcoholicbeverages".upper())
    )
    assert second_reading(passes(looks_different, looks_different)).status == Status.PASS


def test_digits_read_for_letters_dont_count():
    misread = GOVERNMENT_WARNING.replace("ability to drive", "ability 10 drive")
    assert second_reading(passes(misread, misread)).status == Status.PASS


def test_the_second_reading_is_part_of_the_warning_check():
    checks = check_warning(read_warning(GOVERNMENT_WARNING), passes(MISSPELT, MISSPELT))
    assert worst(c.status for c in checks) == Status.REVIEW
    assert check_warning(read_warning(GOVERNMENT_WARNING)) == check_warning(
        read_warning(GOVERNMENT_WARNING), None
    )
