"""tools/heading_weight.py: which labels each setting of the code-side bold check would
send to review."""

from tools.heading_weight import cell, flagged


def test_only_headings_claude_called_bold_and_measured_light_are_flagged():
    rows = [
        {"ai_bold": "yes", "weight": (1.05, 20)},  # flagged
        {"ai_bold": "yes", "weight": (1.05, 10)},  # print too small, if a size is required
        {"ai_bold": "yes", "weight": (1.40, 20)},  # clearly heavier
        {"ai_bold": "cant_tell", "weight": (1.0, 20)},  # Check this already
        {"ai_bold": "yes", "weight": None},  # not measured
    ]
    assert len(flagged(rows, 1.1, 0)) == 2
    assert len(flagged(rows, 1.1, 14)) == 1


def test_a_flag_on_a_real_bold_heading_is_wrong_only_where_the_key_says_matches():
    assert cell([{"key_says_matches": True}, {"key_says_matches": False}]) == "2 (1 wrong)"
    assert cell([{"ai_bold": "yes"}]) == "1"  # samples have no answer key for this
