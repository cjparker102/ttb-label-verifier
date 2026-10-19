"""Label pictures must never be written to disk.

Python's audit hooks report every file opened for writing and every temporary
file created, anywhere in the process. These tests switch the hook on while a
label is checked and fail if anything was written.
"""

import os
import sys
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from starlette.formparsers import MultiPartParser

from app.main import app, get_reader
from tests.stand_ins import ReplayReader
from tests.web.test_check_page import OLD_TOM_FORM

WRITE_FLAGS = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND
watching = False
writes: list[tuple] = []


def watch_for_writes(event: str, args: tuple) -> None:
    if not watching:
        return
    if event == "open":
        path, mode, flags = args
        if isinstance(mode, str) and any(c in mode for c in "wax+"):
            writes.append((event, path, mode))
        elif mode is None and isinstance(flags, int) and flags & WRITE_FLAGS:
            writes.append((event, path, flags))
    elif event in ("tempfile.mkstemp", "tempfile.mkdtemp", "os.mkdir"):
        writes.append((event, *args))


sys.addaudithook(watch_for_writes)  # audit hooks can't be removed; it is idle unless watching


def big_photo() -> bytes:
    """A 2.5 MB picture: well over the 1 MB at which Starlette would normally spill to disk."""
    image = Image.frombytes("RGB", (1000, 850), os.urandom(1000 * 850 * 3))
    out = BytesIO()
    image.save(out, format="PNG")
    assert len(out.getvalue()) > 2 * 1024 * 1024
    return out.getvalue()


def check_while_watching(client: TestClient, photo: bytes) -> list[tuple]:
    global watching
    files = [("images", ("photo.png", photo, "image/png"))]
    client.post("/check", data=OLD_TOM_FORM, files=files)  # warm-up: loads any lazy imports
    writes.clear()
    watching = True
    try:
        response = client.post("/check", data=OLD_TOM_FORM, files=files)
    finally:
        watching = False
    assert response.status_code == 200
    return list(writes)


@pytest.fixture
def client():
    app.dependency_overrides[get_reader] = lambda: ReplayReader()
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_checking_a_label_writes_nothing_to_disk(client):
    assert check_while_watching(client, big_photo()) == []


def test_the_watch_does_catch_a_disk_write(client):
    """Proves the test above can fail: with Starlette's default 1 MB spool limit, a big
    upload spills into a temporary file, and the hook sees it."""
    raised = MultiPartParser.spool_max_size
    MultiPartParser.spool_max_size = 1024 * 1024
    try:
        caught = check_while_watching(client, big_photo())
    finally:
        MultiPartParser.spool_max_size = raised
    assert caught
