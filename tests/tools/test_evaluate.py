import asyncio

import pytest

from app.batch import new_job, run_job
from app.export import results_workbook
from app.intake.matching import MatchedRow
from app.intake.spreadsheet import ApplicationRow
from tests.stand_ins import PerfectReader
from tools.evaluate import (
    application_for,
    judge,
    load_entries,
    markdown,
    percentile,
    result_word,
    results_from_excel,
    summarize,
)
from tools.make_samples import LABELS_DIR


@pytest.mark.parametrize(
    ("expected", "got", "judgment"),
    [
        ("pass", "pass", "exact"),
        ("fail", "pass", "false_pass"),
        ("review", "pass_with_note", "false_pass"),
        ("fail", "not_needed", "false_pass"),
        ("pass", "fail", "false_fail"),
        ("review", "fail", "false_fail"),
        ("fail", "review", "review_instead_of_fail"),
        ("pass", "review", "extra_review"),
        ("not_needed", "review", "extra_review"),
        ("pass", "pass_with_note", "note_difference"),
    ],
)
def test_judging_a_field(expected, got, judgment):
    assert judge(expected, got) == judgment


def test_percentile_is_a_measured_value():
    times = [1.0, 2.0, 3.0, 4.0, 10.0]
    assert percentile(times, 0.95) == 10.0
    assert percentile(times, 0.5) == 3.0


def test_results_read_back_from_the_apps_excel_download():
    entries = load_entries(["ridgewick-rye-wrong-abv", "stones-throw-gin"])
    rows = []
    for number, entry in enumerate(entries, start=2):
        name = entry["images"][0]
        row = ApplicationRow(number, (name,), application_for(entry), (), "brand")
        rows.append(MatchedRow(row, ((name, (LABELS_DIR / name).read_bytes()),), ()))
    job = new_job(rows, [], [])
    reader = PerfectReader([entry["truth"] for entry in entries])
    asyncio.run(run_job(job, reader, 1568, 1, asyncio.Semaphore(1)))

    by_row = results_from_excel(results_workbook(job))
    for number, (entry, item) in enumerate(zip(entries, job.items, strict=True), start=2):
        expected = {field.field: result_word(field) for field in item.outcome.result.fields}
        assert by_row[number]["got"] == expected == entry["expected"]
        assert by_row[number]["read_by"] == "AI reader"


def test_summary_counts_and_report():
    def record(label_id, photo, judgments, seconds):
        return {"id": label_id, "photo": photo, "judgments": judgments, "seconds": seconds}

    results = {
        "mode": "in process",
        "reader": "anthropic",
        "settings": {},
        "measured_at": "2026-10-19T12:00:00",
        "commit": "abc1234",
        "records": [
            record("a", None, {"brand_name": "exact", "net_contents": "exact"}, 2.0),
            record("b", None, {"brand_name": "exact", "net_contents": "false_pass"}, 3.0),
            record("c", "blurry", {"brand_name": "extra_review", "net_contents": "exact"}, 6.0),
            {"id": "d", "photo": None, "error": "NoReader"},
        ],
    }
    summary = summarize(results)
    assert (summary["labels"], summary["errors"]) == (4, 1)
    assert (summary["clean_labels_all_exact"], summary["clean_labels"]) == (1, 2)
    assert (summary["photo_fields_acceptable"], summary["photo_fields"]) == (2, 2)
    assert summary["false_passes"] == ["b: net_contents"]
    assert summary["seconds"]["under_5_seconds"] == 2
    report = markdown(results, summary)
    assert "| False passes (a planted problem shown as Matches) | 1 |" in report
    assert "- b: net_contents" in report


def test_summary_reports_how_many_fields_to_look_at_were_outlined():
    def record(label_id, flagged, outlined):
        return {
            "id": label_id,
            "photo": None,
            "judgments": {"brand_name": "exact"},
            "seconds": 2.0,
            "flagged_on_label": flagged,
            "outlined": outlined,
        }

    results = {
        "mode": "in process",
        "reader": "anthropic",
        "settings": {},
        "measured_at": "2026-10-19T12:00:00",
        "commit": "abc1234",
        "records": [
            record("a", ["alcohol_content", "government_warning"], ["alcohol_content"]),
            record("b", [], []),
            record("c", ["net_contents"], ["net_contents"]),
        ],
    }
    summary = summarize(results)
    assert (summary["outlined"], summary["flagged_on_label"]) == (2, 3)
    report = markdown(results, summary)
    assert "| Fields to look at that were outlined on the picture | 2 of 3 |" in report
