import asyncio
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app.batch import new_job, run_job
from app.export import results_workbook
from app.intake.matching import MatchedRow
from app.intake.spreadsheet import ApplicationRow
from app.main import app, get_reader
from app.reading.ocr import tesseract_available
from tests.stand_ins import PerfectReader
from tools import evaluate
from tools.evaluate import (
    application_for,
    from_page,
    judge,
    load_entries,
    markdown,
    percentile,
    post_check,
    result_word,
    results_from_excel,
    summarize,
)
from tools.make_samples import LABELS_DIR, SAMPLES_DIR

EXPECTED = {e["id"]: e for e in json.loads((SAMPLES_DIR / "expected.json").read_text("utf-8"))}


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


def sample_page(sample_id: str) -> str:
    app.dependency_overrides[get_reader] = lambda: PerfectReader([EXPECTED[sample_id]["truth"]])
    try:
        with TestClient(app) as client:
            return client.post(f"/samples/{sample_id}/check").text
    finally:
        app.dependency_overrides.clear()


@pytest.mark.skipif(not tesseract_available(), reason="Tesseract is not installed")
def test_a_result_page_is_read_back(monkeypatch):
    monkeypatch.setattr("app.checking.OUTLINE_WAIT", 30)  # the page, not the time limit
    shown = from_page(sample_page("ridgewick-rye-wrong-abv"))
    assert shown["read_by"] == "ai"
    assert 0 < shown["server_seconds"] < 60
    assert shown["flagged_on_label"] == shown["outlined"] == ["alcohol_content"]
    assert shown["second_reading"] is True  # as outlines are, Tesseract's words were ready


def test_a_page_with_nothing_to_look_at():
    shown = from_page(sample_page("old-tom-bourbon"))
    assert (shown["flagged_on_label"], shown["outlined"]) == ([], [])


def test_a_check_waits_out_the_apps_limit(monkeypatch):
    answers = iter([429, 429, 200])
    sent = []

    def handler(request):
        sent.append(request.url.path)
        return httpx.Response(next(answers), text="page")

    waits = []
    monkeypatch.setattr(evaluate.time, "sleep", waits.append)
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        response, seconds = post_check(client, "https://app", {"brand_name": "X"}, [])
    assert response.status_code == 200 and seconds < 1
    assert sent == ["/check"] * 3
    assert waits == [evaluate.LIMIT_WAIT] * 2


def test_summary_reports_time_inside_the_app():
    results = {
        "mode": "deployed app",
        "url": "https://app",
        "deployed_as": "revision app--0000017, image 223172b",
        "measured_at": "2026-10-19T12:00:00",
        "commit": "abc1234",
        "records": [
            {"id": i, "photo": None, "judgments": {"brand_name": "exact"}, "seconds": s + 0.5,
             "server_seconds": s}
            for i, s in enumerate([2.0, 3.0, 4.0])
        ],
    }  # fmt: skip
    summary = summarize(results)
    assert summary["server_seconds"] == {"median": 3.0, "p95": 4.0, "max": 4.0}
    report = markdown(results, summary)
    assert "| Of that, time inside the app (median / p95 / max) | 3.0 s / 4.0 s / 4.0 s |" in report
    assert (
        "Commit of this evaluation tool: `abc1234`. "
        "The deployed app: revision app--0000017, image 223172b." in report
    )


def test_how_often_the_second_reading_was_ready_is_reported():
    results = {
        "mode": "in process",
        "reader": "anthropic",
        "settings": {},
        "measured_at": "2026-10-21T09:00:00",
        "commit": "abc1234",
        "records": [
            {
                "id": i,
                "photo": None,
                "read_by": "ai",
                "second_reading": ready,
                "judgments": {"brand_name": "exact"},
                "seconds": 2.0,
            }
            for i, ready in [("a", True), ("b", False), ("c", True)]
        ],
    }
    summary = summarize(results)
    assert (summary["second_reading"], summary["read_by_ai"]) == (2, 3)
    report = markdown(results, summary)
    assert "| Checks where Tesseract's second reading was ready in time | 2 of 3 |" in report


def test_a_run_never_overwrites_an_earlier_one(tmp_path):
    from tools.evaluate import unused

    stem = tmp_path / "real-labels-2026-10-20"
    assert unused(stem, ".md") == stem
    (tmp_path / "real-labels-2026-10-20.md").write_text("first run")
    assert unused(stem, ".md") == tmp_path / "real-labels-2026-10-20-2"
    (tmp_path / "real-labels-2026-10-20-2.json").write_text("second run")
    assert unused(stem, ".json", ".md") == tmp_path / "real-labels-2026-10-20-3"


def test_a_field_is_detected_only_when_its_comparison_raised_it():
    from app.rules.results import Check, Status
    from app.rules.verdict import FieldResult
    from tools.evaluate import cause

    def field(*checks):
        return FieldResult("brand_name", "Brand name", "X", "Y", 1, checks)

    differs = Check(Status.FAIL, 'The label says "Y" but the application says "X".')
    trade_name = Check(Status.REVIEW, "It may be a trade name the company uses. Please check.")
    unclear = Check(Status.REVIEW, "Part of the brand name is hard to read on the label.")
    missing = Check(Status.FAIL, "The label doesn't show the brand name.")
    matches = Check(Status.PASS, "The brand name matches the application.")
    rule = Check(
        Status.REVIEW, "Brand name, class/type, and alcohol content must be on the same side."
    )
    assert cause(field(differs)) == "comparison fail"
    assert cause(field(trade_name)) == "comparison review"
    assert cause(field(unclear)) == "other review"
    assert cause(field(missing)) == "other fail"
    assert cause(field(matches, rule)) == "other review"
    assert cause(field(matches)) == "pass"
