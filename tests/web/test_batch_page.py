"""Batch upload, end to end, with stand-ins for Claude."""

import asyncio
import io
import json
import threading
import time
import zipfile

import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook

from app.intake.spreadsheet import read_spreadsheet
from app.limits import Limits
from app.main import app, get_reader
from tests.disk_watch import watch_disk_writes
from tests.stand_ins import PerfectReader, ReplayReader, expected_word
from tools.make_samples import LABELS_DIR, SAMPLES_DIR

EXPECTED = json.loads((SAMPLES_DIR / "expected.json").read_text(encoding="utf-8"))
SPREADSHEET = (SAMPLES_DIR / "applications.csv").read_bytes()


def planted_counts() -> tuple[int, int, int]:
    """How many sample labels should come out with problems, needing review, and all good."""
    worst = []
    for entry in EXPECTED:
        results = set(entry["expected"].values())
        worst.append("fail" if "fail" in results else "review" if "review" in results else "pass")
    return worst.count("fail"), worst.count("review"), worst.count("pass")


def samples_zip(extra=()) -> bytes:
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as archive:
        for entry in EXPECTED:
            for name in entry["images"]:
                archive.write(LABELS_DIR / name, f"labels/{name}")
        for name, data in extra:
            archive.writestr(name, data)
    return out.getvalue()


@pytest.fixture
def client():
    saved = app.state.batch_concurrency
    with TestClient(app) as test_client:  # keeps the event loop running for background batches
        yield test_client
    app.dependency_overrides.clear()
    app.state.batch_concurrency = saved


def use_reader(reader):
    app.dependency_overrides[get_reader] = lambda: reader


def start(client, spreadsheet=SPREADSHEET, pictures=None, name="labels.zip"):
    files = [
        ("spreadsheet", ("applications.csv", spreadsheet, "text/csv")),
        (
            "pictures",
            (name, pictures if pictures is not None else samples_zip(), "application/zip"),
        ),
    ]
    return client.post("/batches", files=files, follow_redirects=False)


def wait_until_finished(client, url, timeout=30):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        progress = client.get(f"{url}/progress").json()
        if progress["state"] == "finished":
            return progress
        time.sleep(0.05)
    raise AssertionError("the batch did not finish")


def run_samples_batch(client, extra=()):
    use_reader(PerfectReader([entry["truth"] for entry in EXPECTED]))
    app.state.batch_concurrency = 1  # one at a time, so readings come back in row order
    response = start(client, pictures=samples_zip(extra))
    assert response.status_code == 303
    url = response.headers["location"]
    wait_until_finished(client, url)
    return url


def test_every_sample_in_a_batch_gets_its_expected_results(client):
    url = run_samples_batch(client)
    job = app.state.batches.get(url.rsplit("/", 1)[-1])
    items = sorted(job.items, key=lambda item: item.row_number)
    assert len(items) == len(EXPECTED)
    for item, entry in zip(items, EXPECTED, strict=True):
        got = {field.field: expected_word(field) for field in item.outcome.result.fields}
        assert got == entry["expected"], entry["id"]


def test_results_page_shows_problems_first_and_the_counts(client):
    url = run_samples_batch(client, extra=[("readme.txt", b"notes"), (".DS_Store", b"x")])
    page = client.get(url).text
    assert f"{len(EXPECTED)} of {len(EXPECTED)} labels checked." in page
    fails, reviews, passes = planted_counts()
    assert f"Problems found in {fails} labels" in page
    assert f"{reviews} labels need review" in page
    assert f"{passes} labels all good" in page
    assert "Download results (Excel)" in page
    assert page.index("RIDGEWICK") < page.index("TIDEWICK")  # a problem comes before a pass
    assert page.count("Checked in ") >= len(EXPECTED)  # the time each label took
    assert "labels.zip: readme.txt" in page
    assert "labels.zip: .DS_Store" in page


def test_excel_download_has_every_label(client):
    url = run_samples_batch(client)
    response = client.get(f"{url}/results.xlsx")
    assert response.status_code == 200
    assert "spreadsheetml" in response.headers["content-type"]
    assert "attachment" in response.headers["content-disposition"]
    summary = load_workbook(io.BytesIO(response.content))["Summary"]
    assert summary.max_row == len(EXPECTED) + 1  # the headings, then one row per label


def test_previews_are_served_from_memory(client):
    url = run_samples_batch(client)
    preview = client.get(f"{url}/previews/2.jpg")
    assert preview.status_code == 200
    assert preview.headers["content-type"] == "image/jpeg"
    assert client.get(f"{url}/previews/99.jpg").status_code == 404


def test_while_running_the_page_says_so_and_excel_waits(client):
    hold = threading.Event()

    class HeldReader(ReplayReader):
        async def read(self, images):
            while not hold.is_set():
                await asyncio.sleep(0.01)
            return await super().read(images)

    use_reader(HeldReader())
    url = start(client).headers["location"]
    try:
        page = client.get(url).text
        assert "This page updates by itself." in page
        assert '<meta http-equiv="refresh" content="5">' in page  # for browsers without scripts
        assert client.get(f"{url}/results.xlsx").status_code == 409
        assert client.get(f"{url}/progress").json()["state"] in ("queued", "running")
    finally:
        hold.set()
    wait_until_finished(client, url)


def test_rows_whose_pictures_are_missing_are_reported(client):
    use_reader(ReplayReader())
    # The spreadsheet names a picture that isn't in the ZIP, and so leaves one unused.
    sheet = SPREADSHEET.replace(b"stones-throw-gin.png", b"missing.png")
    url = start(client, spreadsheet=sheet).headers["location"]
    wait_until_finished(client, url)
    page = client.get(url).text
    assert "These pictures were not in the upload: missing.png." in page
    assert "1 label could not be checked" in page
    assert "<strong>stones-throw-gin.png</strong>: No row in the spreadsheet lists" in page


def test_spreadsheet_template_downloads_and_reads_back(client):
    response = client.get("/template.csv")
    assert response.status_code == 200
    assert "attachment" in response.headers["content-disposition"]
    rows = read_spreadsheet("template.csv", response.content)
    assert [row.problems for row in rows] == [(), ()]


@pytest.mark.parametrize(
    ("spreadsheet", "pictures", "message"),
    [
        (b"brand\nOLD TOM\n", None, "needs a column for"),
        (SPREADSHEET, b"not a zip", "could not be opened"),
    ],
)
def test_unusable_uploads_say_why(client, spreadsheet, pictures, message):
    use_reader(ReplayReader())
    response = start(client, spreadsheet=spreadsheet, pictures=pictures)
    assert response.status_code == 422
    assert message in response.text


def test_missing_spreadsheet_or_pictures(client):
    use_reader(ReplayReader())
    response = client.post(
        "/batches", files=[("pictures", ("a.zip", samples_zip(), "application/zip"))]
    )
    assert "Add the spreadsheet of applications." in response.text
    response = client.post("/batches", files=[("spreadsheet", ("a.csv", SPREADSHEET, "text/csv"))])
    assert "Add the label pictures, or a ZIP file of them." in response.text


def test_batch_limits_are_enforced(client):
    use_reader(ReplayReader())
    app.state.limits = Limits(1000, 600, 0, 3600, 100_000)  # no batches allowed
    response = start(client)
    assert response.status_code == 429
    assert "batches" in response.text


def test_expired_or_unknown_batches(client):
    assert client.get("/batches/no-such-batch").status_code == 404
    assert "no longer available" in client.get("/batches/no-such-batch").text
    assert client.get("/batches/no-such-batch/progress").json() == {"state": "gone"}


def test_a_whole_batch_writes_nothing_to_disk(client):
    url = run_samples_batch(client)  # warm-up: loads any lazy imports
    client.get(f"{url}/results.xlsx")
    with watch_disk_writes() as writes:
        url = run_samples_batch(client)
        client.get(url)
        client.get(f"{url}/results.xlsx")
    assert list(writes) == []


def test_a_batch_sent_as_a_7z_file(client):
    from tests.intake.test_sevenzip import make_7z

    use_reader(ReplayReader())
    pictures = [(name, (LABELS_DIR / name).read_bytes()) for e in EXPECTED for name in e["images"]]
    response = start(client, pictures=make_7z(*pictures), name="labels.7z")
    assert response.status_code == 303
    progress = wait_until_finished(client, response.headers["location"])
    assert progress["done"] == progress["total"] == len(EXPECTED)
