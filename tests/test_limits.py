import asyncio

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


def upload_scope(size: int | None, method: str = "POST") -> dict:
    headers = [] if size is None else [(b"content-length", str(size).encode())]
    return {"type": "http", "method": method, "headers": headers}


class Uploads:
    """Requests that stay in the app until let go, so several are handled at once."""

    def __init__(self, max_bytes: int, max_receiving_bytes: int):
        self.release = asyncio.Event()
        self.handled = 0

        async def inner(scope, receive, send):
            self.handled += 1
            await self.release.wait()
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b""})

        self.limit = RequestSizeLimit(inner, max_bytes, max_receiving_bytes)

    async def send(self, size: int | None, method: str = "POST") -> int:
        statuses = []

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message):
            if message["type"] == "http.response.start":
                statuses.append(message["status"])

        await self.limit(upload_scope(size, method), receive, send)
        return statuses[0]


def test_a_new_upload_waits_while_others_being_handled_fill_the_cap():
    async def run():
        uploads = Uploads(max_bytes=100, max_receiving_bytes=150)
        first = asyncio.create_task(uploads.send(100))
        await asyncio.sleep(0)
        assert await uploads.send(60) == 503  # 160 bytes at once is too many
        small = asyncio.create_task(uploads.send(50))  # 150 fits
        await asyncio.sleep(0)
        page = asyncio.create_task(uploads.send(None, "GET"))  # pages still load
        await asyncio.sleep(0)
        assert uploads.handled == 3
        uploads.release.set()
        assert await page == 200
        assert (await first, await small) == (200, 200)
        assert uploads.limit.receiving == 0
        assert await uploads.send(100) == 200  # room again once they are done

    asyncio.run(run())


def test_one_upload_alone_is_always_let_in_and_pages_are_never_counted():
    async def run():
        uploads = Uploads(max_bytes=100, max_receiving_bytes=50)
        uploads.release.set()
        assert await uploads.send(100) == 200
        assert await uploads.send(None, "GET") == 200
        assert uploads.limit.receiving == 0

    asyncio.run(run())


def test_a_body_without_its_size_counts_as_the_largest_allowed():
    async def run():
        uploads = Uploads(max_bytes=100, max_receiving_bytes=150)
        first = asyncio.create_task(uploads.send(None))  # sent in pieces
        await asyncio.sleep(0)
        assert uploads.limit.receiving == 100
        assert await uploads.send(60) == 503
        uploads.release.set()
        assert await first == 200

    asyncio.run(run())


def test_the_app_limits_batch_uploads_to_400_mb():
    from app.config import MB, Settings

    settings = Settings()
    assert settings.max_request_bytes == 410 * MB  # 400 MB of pictures plus the spreadsheet
    # A single check still fits beside the largest batch while it arrives.
    largest_check = settings.max_images_per_label * settings.max_image_bytes
    assert settings.max_receiving_bytes >= settings.max_request_bytes + largest_check
    # 300 labels of about 0.9 MB, about 270 MB, fit with room to spare.
    assert 300 * 0.9 * 1e6 < 0.7 * settings.max_request_bytes
