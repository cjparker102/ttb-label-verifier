"""The single-label page, end to end, with a stand-in for Claude."""

import pytest
from fastapi.testclient import TestClient

from app.limits import Limits
from app.main import app, get_reader
from app.reading.schema import FieldReading
from tests.stand_ins import FailingReader, ReplayReader, recorded_reading
from tools.make_samples import LABELS_DIR

OLD_TOM_FORM = {
    "beverage_type": "distilled_spirits",
    "brand_name": "OLD TOM DISTILLERY",
    "class_type": "Kentucky Straight Bourbon Whiskey",
    "alcohol_content": "45% Alc./Vol. (90 Proof)",
    "net_contents": "750 mL",
    "bottler_name_address": "Old Tom Distillery, Bardstown, Kentucky",
    "country_of_origin": "",
}


def label_files():
    return [
        ("images", (name, (LABELS_DIR / name).read_bytes(), "image/png"))
        for name in ("old-tom-bourbon_front.png", "old-tom-bourbon_back.png")
    ]


@pytest.fixture
def use_reader():
    """Swap in a reader for one test, then put things back."""

    def swap(reader):
        app.dependency_overrides[get_reader] = lambda: reader
        return reader

    yield swap
    app.dependency_overrides.clear()


client = TestClient(app)


def test_home_page_has_the_form():
    page = client.get("/").text
    assert 'action="/check"' in page
    assert 'type="file" id="images" name="images"' in page
    for name in OLD_TOM_FORM:
        assert f'id="{name}"' in page
    assert "Malt beverage (beer)" in page
    assert ">Check label</button>" in page


def test_clean_label_shows_all_good(use_reader):
    reader = use_reader(ReplayReader())
    response = client.post("/check", data=OLD_TOM_FORM, files=label_files())
    page = response.text
    assert response.status_code == 200
    assert "All good" in page
    assert "Checked in" in page
    assert "7 fields match or are not needed (show)" in page
    assert "Fields to look at" not in page
    assert page.count('src="data:image/jpeg;base64,') == 2
    assert len(reader.received[0]) == 2  # both pictures were read together


def test_mismatch_shows_the_problem_and_why(use_reader):
    use_reader(ReplayReader())
    form = {**OLD_TOM_FORM, "alcohol_content": "40% Alc./Vol. (80 Proof)"}
    page = client.post("/check", data=form, files=label_files()).text
    assert "Problems found (1)" in page
    assert "Fields to look at" in page
    assert "The label says 45% but the application says 40%." in page


def test_the_form_is_empty_after_a_check(use_reader):
    use_reader(ReplayReader())
    page = client.post("/check", data=OLD_TOM_FORM, files=label_files()).text
    assert 'value="OLD TOM DISTILLERY"' not in page
    assert "Check another label" in page


def test_missing_pictures_keeps_what_was_typed(use_reader):
    use_reader(ReplayReader())
    response = client.post("/check", data=OLD_TOM_FORM)
    assert response.status_code == 422
    assert "Add at least one picture of the label." in response.text
    assert 'value="OLD TOM DISTILLERY"' in response.text


def test_missing_product_type_and_required_fields(use_reader):
    use_reader(ReplayReader())
    form = {**OLD_TOM_FORM, "beverage_type": "", "brand_name": ""}
    page = client.post("/check", data=form, files=label_files()).text
    assert "Choose the type of product." in page
    assert "Fill in the brand name." in page
    assert "please choose them again" in page


def test_a_file_that_is_not_an_image_is_named(use_reader):
    use_reader(ReplayReader())
    files = [("images", ("notes.txt", b"not a picture", "text/plain"))]
    response = client.post("/check", data=OLD_TOM_FORM, files=files)
    assert response.status_code == 422
    assert "&#34;notes.txt&#34; is not an image this app can read." in response.text


def test_too_many_pictures(use_reader):
    use_reader(ReplayReader())
    files = label_files() * 4  # 8 pictures
    response = client.post("/check", data=OLD_TOM_FORM, files=files)
    assert response.status_code == 422
    assert "no more than 6 pictures" in response.text


def test_reader_failure_gives_a_plain_message(use_reader):
    use_reader(FailingReader())
    response = client.post("/check", data=OLD_TOM_FORM, files=label_files())
    assert response.status_code == 503
    assert "could not read this label just now" in response.text


def test_missing_reader_setup_is_reported(use_reader):
    use_reader(None)
    response = client.post("/check", data=OLD_TOM_FORM, files=label_files())
    assert response.status_code == 422
    assert "not set up on this server" in response.text


def test_label_text_is_shown_as_text_never_run(use_reader):
    reading = recorded_reading()
    sneaky = FieldReading(
        text="<script>alert(1)</script>", readability="clear", image_number=1, english_meaning=None
    )
    use_reader(ReplayReader(reading.model_copy(update={"brand_name": sneaky})))
    page = client.post("/check", data=OLD_TOM_FORM, files=label_files()).text
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in page
    assert "<script>alert(1)" not in page


def test_security_headers():
    headers = client.get("/").headers
    assert "default-src 'self'" in headers["content-security-policy"]
    assert "frame-ancestors 'none'" in headers["content-security-policy"]
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["cache-control"] == "no-store"


def test_stylesheet_and_script_are_served_by_the_app():
    for path in ("/static/style.css", "/static/app.js"):
        assert client.get(path).status_code == 200


def test_reader_failure_is_logged_without_label_details(use_reader, caplog):
    use_reader(FailingReader())
    with caplog.at_level("WARNING", logger="ttb_label_verifier"):
        client.post("/check", data=OLD_TOM_FORM, files=label_files())
    assert "Label reading failed: ReadingFailed" in caplog.text
    assert "OLD TOM" not in caplog.text


def test_too_many_checks_from_one_visitor_are_refused(use_reader):
    use_reader(ReplayReader())
    app.state.limits = Limits(1, 600, 3, 3600, 100)
    assert client.post("/check", data=OLD_TOM_FORM, files=label_files()).status_code == 200
    response = client.post("/check", data=OLD_TOM_FORM, files=label_files())
    assert response.status_code == 429
    assert "Please wait a few minutes" in response.text


def test_form_mistakes_do_not_use_up_the_limit(use_reader):
    use_reader(ReplayReader())
    app.state.limits = Limits(1, 600, 3, 3600, 100)
    client.post("/check", data=OLD_TOM_FORM)  # no pictures: refused before reading
    assert client.post("/check", data=OLD_TOM_FORM, files=label_files()).status_code == 200
