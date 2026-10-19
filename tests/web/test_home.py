from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_home_page_shows_app_name():
    response = client.get("/")
    assert response.status_code == 200
    assert "<title>TTB Label Verifier</title>" in response.text


def test_health_check_reports_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_docs_are_turned_off():
    for path in ("/docs", "/redoc", "/openapi.json"):
        assert client.get(path).status_code == 404
