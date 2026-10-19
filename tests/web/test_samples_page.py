"""The "Try a sample" buttons, with stand-ins for Claude."""

import json
import time

import pytest
from fastapi.testclient import TestClient
from markupsafe import escape

from app.limits import Limits
from app.main import app, get_reader
from app.samples import FEATURED, featured, pictures, sample_labels
from tests.stand_ins import PerfectReader, ReplayReader
from tools.make_samples import SAMPLES_DIR

EXPECTED = {e["id"]: e for e in json.loads((SAMPLES_DIR / "expected.json").read_text("utf-8"))}


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def use_reader(reader):
    app.dependency_overrides[get_reader] = lambda: reader


def test_every_sample_loads_with_its_application_and_pictures():
    labels = sample_labels()
    assert set(labels) == set(EXPECTED)
    for label in labels.values():
        assert label.row.application is not None, label.id
        assert len(pictures(label)) == len(EXPECTED[label.id]["images"])


def test_featured_samples_exist_in_order():
    assert [label.id for label in featured()] == list(FEATURED)


def test_home_page_offers_the_samples_first(client):
    page = client.get("/").text
    assert page.index("Try it with a sample label") < page.index("Check one label")
    for sample_id, title in FEATURED.items():
        assert f'action="/samples/{sample_id}/check"' in page
        assert str(escape(title)) in page  # escaped the way the templates escape all text
    assert f"Try a sample batch of all {len(EXPECTED)} labels" in page


def test_a_sample_check_shows_its_results_and_what_was_planted(client):
    sample_id = "ridgewick-rye-wrong-abv"
    use_reader(PerfectReader([EXPECTED[sample_id]["truth"]]))
    page = client.post(f"/samples/{sample_id}/check").text
    assert "Problems found (1)" in page
    assert "Sample label: Alcohol content that doesn&#39;t match." in page
    assert "the application says 45% (90 proof)" in page
    assert "The label says 46% but the application says 45%." in page
    assert "Try another sample label" in page


def test_two_picture_sample_sends_both_pictures(client):
    reader = ReplayReader()
    use_reader(reader)
    assert client.post("/samples/old-tom-bourbon/check").status_code == 200
    assert len(reader.received[0]) == 2


def test_unknown_sample(client):
    response = client.post("/samples/no-such-label/check")
    assert response.status_code == 404
    assert "no sample label with that name" in response.text


def test_sample_checks_count_toward_the_limits(client):
    use_reader(ReplayReader())
    app.state.limits = Limits(1, 600, 3, 3600, 100)
    assert client.post("/samples/old-tom-bourbon/check").status_code == 200
    assert client.post("/samples/old-tom-bourbon/check").status_code == 429


def test_the_sample_batch_checks_every_sample(client):
    use_reader(ReplayReader())
    response = client.post("/samples/batch", follow_redirects=False)
    assert response.status_code == 303
    url = response.headers["location"]
    deadline = time.monotonic() + 30
    while (progress := client.get(f"{url}/progress").json())["state"] != "finished":
        assert time.monotonic() < deadline
        time.sleep(0.05)
    assert progress["done"] == progress["total"] == len(EXPECTED)
