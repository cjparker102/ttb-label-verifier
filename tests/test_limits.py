from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.limits import RequestSizeLimit


def small_app(max_bytes: int) -> TestClient:
    inner = FastAPI()

    @inner.post("/")
    async def echo(request: Request):
        return {"received": len(await request.body())}

    inner.add_middleware(RequestSizeLimit, max_bytes=max_bytes)
    return TestClient(inner)


def test_request_under_the_limit_passes():
    response = small_app(100).post("/", content=b"x" * 100)
    assert response.json() == {"received": 100}


def test_declared_size_over_the_limit_is_refused_before_reading():
    response = small_app(100).post("/", content=b"x" * 101)
    assert response.status_code == 413
    assert "too large" in response.text


def test_streamed_body_over_the_limit_is_refused():
    def chunks():  # no Content-Length header: the body is sent in pieces
        for _ in range(5):
            yield b"x" * 50

    response = small_app(100).post("/", content=chunks())
    assert response.status_code == 413


def test_nonsense_content_length_is_refused():
    response = small_app(100).post("/", content=b"x", headers={"content-length": "lots"})
    assert response.status_code == 400
