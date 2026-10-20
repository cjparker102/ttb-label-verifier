import re

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_home_page_shows_app_name():
    response = client.get("/")
    assert response.status_code == 200
    assert "<title>TTB Label Verifier</title>" in response.text


def test_every_page_says_it_is_not_an_official_website():
    for page in (client.get("/"), client.get("/batches/no-such-batch")):
        assert "Prototype. Not an official TTB or U.S. government website." in page.text


def test_health_check_reports_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_docs_are_turned_off():
    for path in ("/docs", "/redoc", "/openapi.json"):
        assert client.get(path).status_code == 404


JUMP_LINK = re.compile(r'<a class="jump-link" href="#([\w-]+)">([^<]+)<')


def test_big_links_at_the_top_jump_down_to_each_way_of_checking():
    page = client.get("/").text
    links = JUMP_LINK.findall(page)
    assert [text.strip() for _, text in links] == [
        "Try a sample",
        "Check one label",
        "Check many labels",
    ]
    assert page.index('class="jump-links"') < page.index('id="samples"')  # at the top
    for target, _ in links:
        assert page.count(f'id="{target}"') == 1
    assert 'id="check-one"' in page[page.index("<section") : page.index('action="/check"')]
    assert (
        'id="check-many"' in page[page.index('action="/check"') : page.index('action="/batches"')]
    )


def test_no_sample_link_when_the_server_has_no_samples(monkeypatch):
    monkeypatch.setattr("app.main.featured", lambda: [])
    links = JUMP_LINK.findall(client.get("/").text)
    assert [target for target, _ in links] == ["check-one", "check-many"]
