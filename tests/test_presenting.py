import json

from app.presenting import rules_checked
from app.rules.verdict import check_label
from tests.rules.test_verdict import application_for
from tests.stand_ins import perfect_reading
from tools.make_samples import SAMPLES_DIR

EXPECTED = {e["id"]: e for e in json.loads((SAMPLES_DIR / "expected.json").read_text("utf-8"))}


def fields_of(sample_id):
    entry = EXPECTED[sample_id]
    result = check_label(application_for(sample_id), perfect_reading(entry["truth"]))
    return {field.field: field for field in result.fields}


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
