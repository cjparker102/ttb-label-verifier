"""Structural accessibility checks on every kind of page the app renders.

These don't replace trying the pages with a keyboard and a screen reader, but they
stop the basics from slipping: labels, alt text, language, headings, and results
that never rely on color or icons alone.
"""

import re
import time
from html.parser import HTMLParser

import pytest
from fastapi.testclient import TestClient

from app.main import app, get_reader
from tests.stand_ins import ReplayReader
from tests.web.test_batch_page import SPREADSHEET, samples_zip
from tests.web.test_check_page import OLD_TOM_FORM, label_files


class Page(HTMLParser):
    def __init__(self, html: str):
        super().__init__()
        self.html_lang = None
        self.label_targets: set[str] = set()
        self.controls: list[dict] = []
        self.images: list[dict] = []
        self.h1_count = 0
        self.badges: list[str] = []
        self.title = ""
        self._in_badge = 0
        self._badge_text = ""
        self._in_hidden = 0
        self._in_title = False
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html":
            self.html_lang = a.get("lang")
        elif tag == "label" and a.get("for"):
            self.label_targets.add(a["for"])
        elif tag in ("input", "select", "textarea") and a.get("type") not in ("hidden", "submit"):
            self.controls.append(a)
        elif tag == "img":
            self.images.append(a)
        elif tag == "h1":
            self.h1_count += 1
        elif tag == "title":
            self._in_title = True
        if tag == "span" and "badge" in (a.get("class") or "").split():
            self._in_badge, self._badge_text = 1, ""
        elif tag == "span" and self._in_badge:
            self._in_badge += 1
            if a.get("aria-hidden") == "true":
                self._in_hidden = self._in_badge

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        if tag == "span" and self._in_badge:
            if self._in_hidden == self._in_badge:
                self._in_hidden = 0
            self._in_badge -= 1
            if self._in_badge == 0:
                self.badges.append(self._badge_text.strip())

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        if self._in_badge and not self._in_hidden:
            self._badge_text += data


def check_page(html: str):
    page = Page(html)
    assert page.html_lang == "en"
    assert page.title.strip() == "TTB Label Verifier"
    assert page.h1_count == 1
    for control in page.controls:
        assert control.get("id") in page.label_targets, f"no label for {control}"
    for image in page.images:
        assert (image.get("alt") or "").strip(), f"no alt text for {image}"
    for badge in page.badges:
        assert re.search(r"[A-Za-z]", badge), f"badge without words: {badge!r}"
    return page


@pytest.fixture
def client():
    app.dependency_overrides[get_reader] = lambda: ReplayReader()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_home_page(client):
    page = check_page(client.get("/").text)
    assert len(page.controls) >= 9  # every field of both forms is labelled


def test_single_label_results(client):
    form = {**OLD_TOM_FORM, "alcohol_content": "40%"}
    page = check_page(client.post("/check", data=form, files=label_files()).text)
    assert "Problem" in page.badges
    assert page.images  # the label preview, with alt text


def test_error_page(client):
    check_page(client.post("/check", data=OLD_TOM_FORM).text)


def test_batch_results(client):
    files = [
        ("spreadsheet", ("applications.csv", SPREADSHEET, "text/csv")),
        ("pictures", ("labels.zip", samples_zip(), "application/zip")),
    ]
    url = client.post("/batches", files=files, follow_redirects=False).headers["location"]
    deadline = time.monotonic() + 30
    while client.get(f"{url}/progress").json()["state"] != "finished":
        assert time.monotonic() < deadline
        time.sleep(0.05)
    page = check_page(client.get(url).text)
    assert page.badges
