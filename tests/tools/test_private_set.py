"""A private set of real labels: read from private/, and published only as totals."""

import json
import shutil
import subprocess

import pytest

from tools.evaluate import application_for, judge, pictures_of, summarize
from tools.make_samples import LABELS_DIR
from tools.private_set import NotPrivate, load_cases, public_markdown, public_summary

CASES = [
    {
        "id": "26002001000021",
        "ttb_id": "26002001000021",
        "kind": "as approved",
        "beverage_type": "distilled_spirits",
        "application": {
            "brand_name": "SECRET BRAND",
            "class_type": "Straight Bourbon Whiskey",
            "alcohol_content": "45% Alc./Vol.",
            "net_contents": "750 mL",
            "bottler_name_address": "Secret Distilling, Nashville, Indiana",
            "country_of_origin": "",
        },
        "images": ["labels/26002001000021/images/1.png"],
        "expected": {"brand_name": "pass", "net_contents": ["pass", "review"]},
    },
    {
        "id": "26002001000021-planted",
        "ttb_id": "26002001000021",
        "kind": "planted",
        "planted_field": "brand_name",
        "beverage_type": "distilled_spirits",
        "application": {"brand_name": "OTHER BRAND", "class_type": "x", "net_contents": "1 L",
                        "bottler_name_address": "x"},
        "images": ["labels/26002001000021/images/1.png"],
        "expected": {"brand_name": "fail", "net_contents": "pass"},
    },
]  # fmt: skip


@pytest.fixture
def private_set(tmp_path, monkeypatch):
    """A set in a folder git ignores, as private/ is."""
    folder = tmp_path / "private" / "cola"
    (folder / "labels" / "26002001000021" / "images").mkdir(parents=True)
    shutil.copy(
        LABELS_DIR / "old-tom-bourbon_front.png", folder / "labels/26002001000021/images/1.png"
    )
    (folder / "cases.json").write_text(json.dumps(CASES))
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".gitignore").write_text("private/\n")
    subprocess.run(["git", "init", "-q"], check=True)
    return folder / "cases.json"


def test_cases_bring_their_own_application_and_pictures(private_set):
    cases = load_cases(private_set)
    application = application_for(cases[0])
    assert application.brand_name == "SECRET BRAND"
    assert application.beverage_type.value == "distilled_spirits"
    [(name, data)] = pictures_of(cases[0])
    assert name == "1.png"
    assert data == (LABELS_DIR / "old-tom-bourbon_front.png").read_bytes()


def test_a_set_git_would_commit_is_refused(private_set, tmp_path):
    shown = tmp_path / "cases.json"
    shutil.copy(private_set, shown)
    with pytest.raises(NotPrivate):
        load_cases(shown)


def test_where_more_than_one_result_is_right_any_of_them_is_exact():
    assert judge(["pass", "review"], "review") == "exact"
    assert judge(["pass", "review"], "fail") == "false_fail"
    assert judge(["fail", "review"], "pass") == "false_pass"


def test_the_public_report_has_totals_and_ids_but_nothing_about_any_one_label(private_set):
    cases = load_cases(private_set)
    results = {
        "mode": "in process",
        "measured_at": "2026-10-20T09:00:00",
        "commit": "abc1234",
        "settings": {"model": "claude-haiku-5-5"},
        "records": [
            {
                "id": "26002001000021",
                "photo": None,
                "seconds": 2.5,
                "read_by": "ai",
                "reading": {"brand_name": {"text": "SECRET BRAND"}},
                "got": {"brand_name": "pass", "net_contents": "review"},
                "judgments": {"brand_name": "exact", "net_contents": "exact"},
            },
            {
                "id": "26002001000021-planted",
                "photo": None,
                "seconds": 3.1,
                "read_by": "ai",
                "got": {"brand_name": "fail", "net_contents": "pass"},
                "judgments": {"brand_name": "exact", "net_contents": "exact"},
            },
        ],
    }
    totals = public_summary(cases, results, summarize(results))
    assert totals["approved_all_fine"] == 1
    assert totals["planted_caught_as_problem"] == 1
    assert totals["by_type"] == {"distilled spirits": 1}
    page = public_markdown(results, totals)
    assert "- 26002001000021" in page
    assert "| Planted problems shown as Problem | 1 of 1 |" in page
    for private in ("SECRET", "Secret Distilling", "Nashville", "750 mL", "OTHER BRAND"):
        assert private not in page
    for line in page.splitlines():  # an ID never shares a line with a result
        if "26002001000021" in line:
            assert line == "- 26002001000021"
