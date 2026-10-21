import json

from app.presenting import field_row, rules_checked
from app.rules.verdict import check_label
from app.rules.warning import NOT_CONFIRMED
from tests.rules.test_verdict import application_for
from tests.stand_ins import perfect_reading, perfect_weight
from tools.make_samples import SAMPLES_DIR

EXPECTED = {e["id"]: e for e in json.loads((SAMPLES_DIR / "expected.json").read_text("utf-8"))}


def fields_of(sample_id, measured=False):
    """The sample's results from a perfect reading; with `measured`, its warning heading
    measured too, as code would find it."""
    truth = EXPECTED[sample_id]["truth"]
    heading = perfect_weight(truth) if measured else None
    result = check_label(application_for(sample_id), perfect_reading(truth), heading=heading)
    return {field.field: field for field in result.fields}


def rule_results(field):
    return {r["section"]: r["result"] for r in rules_checked(field)}


def test_a_bold_heading_confirmed_by_measuring_is_met():
    warning = fields_of("old-tom-bourbon", measured=True)["government_warning"]
    assert rule_results(warning) == {"27 CFR 16.21": "met", "27 CFR 16.22(a)(2)": "met"}
    row = field_row(warning)
    assert row["word"] == "Matches"
    assert NOT_CONFIRMED not in [reason["text"] for reason in row["reasons"]]


def test_a_bold_heading_on_the_ai_readers_word_alone_is_never_shown_as_met():
    warning = fields_of("old-tom-bourbon")["government_warning"]
    assert rule_results(warning) == {"27 CFR 16.21": "met", "27 CFR 16.22(a)(2)": "not confirmed"}
    row = field_row(warning)
    assert row["word"] == "Matches, bold not confirmed"
    assert row["view"]["word"] == "Matches"  # the result is kept
    assert NOT_CONFIRMED in [reason["text"] for reason in row["reasons"]]


def test_a_bold_heading_not_confirmed_is_shown_beside_other_problems():
    row = field_row(fields_of("heronmere-gin-warning-wording")["government_warning"])
    reasons = [reason["text"] for reason in row["reasons"]]
    assert row["word"] == "Problem" and NOT_CONFIRMED in reasons and len(reasons) > 1


def test_each_rule_behind_a_field_is_listed_once_with_its_result():
    fields = fields_of("stones-throw-gin")
    alcohol = {r["section"]: r["result"] for r in rules_checked(fields["alcohol_content"])}
    assert alcohol == {"27 CFR 5.65(b)": "met"}
    net = {r["section"]: r["result"] for r in rules_checked(fields["net_contents"])}
    assert net == {"27 CFR 5.70(a)": "met", "27 CFR 5.203(a)": "met"}


def test_several_checks_under_one_section_show_the_worst_result():
    warning = {
        r["section"]: r["result"]
        for r in rules_checked(
            fields_of("copperfen-vodka-title-case-warning")["government_warning"]
        )
    }
    # Wording is right (16.21), but the capitals check under 16.22(a)(2) fails.
    assert warning == {"27 CFR 16.21": "met", "27 CFR 16.22(a)(2)": "not met"}


def test_rule_links_point_to_the_ecfr():
    for rule in rules_checked(fields_of("old-tom-bourbon")["government_warning"]):
        assert rule["url"].startswith("https://www.ecfr.gov/current/title-27/section-16.2")


def test_fields_without_ttb_rules_list_none():
    assert rules_checked(fields_of("old-tom-bourbon")["class_type"]) == []


def test_track_changes_appear_only_when_the_warning_wording_differs():
    changed = field_row(fields_of("heronmere-gin-warning-wording")["government_warning"])
    assert ("missing", "a car") in changed["track"]
    # Wrong capitals alone is not a wording difference.
    assert (
        field_row(fields_of("copperfen-vodka-title-case-warning")["government_warning"])["track"]
        is None
    )
    assert field_row(fields_of("old-tom-bourbon")["government_warning"])["track"] is None
