"""7z safety. Every archive here is built in memory by the test itself."""

import io

import py7zr
import pytest

from app.intake import archives
from app.intake.archives import (
    ArchiveError,
    CappedFactory,
    OverLimit,
    collect_pictures,
    unpack_7z,
)
from tests.disk_watch import watch_disk_writes
from tests.intake.test_archives import JPEG, PNG, make_zip


def make_7z(*entries, password=None) -> bytes:
    out = io.BytesIO()
    options = {"password": password, "header_encryption": True} if password else {}
    with py7zr.SevenZipFile(out, "w", **options) as archive:
        for name, data in entries:
            archive.writestr(data, name)
    return out.getvalue()


def reasons(unpacked):
    return {s.name: s.reason for s in unpacked.skipped}


def test_pictures_come_out_by_file_name_without_folders():
    unpacked = unpack_7z(make_7z(("labels/front.png", PNG), ("labels/back.jpg", JPEG)))
    assert unpacked.pictures == {"front.png": PNG, "back.jpg": JPEG}
    assert unpacked.skipped == []


def test_clutter_and_non_pictures_are_skipped_and_listed():
    unpacked = unpack_7z(
        make_7z(("front.png", PNG), (".DS_Store", b"x" * 40), ("notes.txt", b"hello" * 20))
    )
    assert list(unpacked.pictures) == ["front.png"]
    assert set(reasons(unpacked)) == {".DS_Store", "notes.txt"}


def test_password_protected_7z_files_say_so():
    with pytest.raises(ArchiveError, match="password-protected"):
        unpack_7z(make_7z(("front.png", PNG), password="secret"))


def test_7z_bombs_are_refused_before_unpacking():
    with pytest.raises(ArchiveError, match="packed far more tightly"):
        unpack_7z(make_7z(("bomb.png", b"\0" * (2 * 1024 * 1024))))


def test_oversized_pictures_are_skipped(monkeypatch):
    monkeypatch.setattr(archives, "MAX_PICTURE_BYTES", 100)
    unpacked = unpack_7z(make_7z(("big.png", PNG), ("small.png", PNG[:90])))
    assert "Larger than" in reasons(unpacked)["big.png"]


def test_unpacking_stops_once_a_file_goes_over_its_limit(monkeypatch):
    # In case a listing lies about a file's size, the writer itself stops the unpacking.
    monkeypatch.setattr(archives, "MAX_PICTURE_BYTES", 10)
    writer = CappedFactory().create("big.png")
    writer.write(b"0123456789")
    with pytest.raises(OverLimit):
        writer.write(b"x")


def test_the_whole_archive_shares_one_budget(monkeypatch):
    monkeypatch.setattr(archives, "MAX_TOTAL_BYTES", 15)
    factory = CappedFactory()
    factory.create("a.png").write(b"0123456789")
    with pytest.raises(OverLimit):
        factory.create("b.png").write(b"0123456789")


def test_too_many_items(monkeypatch):
    monkeypatch.setattr(archives, "MAX_ITEMS", 2)
    with pytest.raises(ArchiveError, match="holds 3 items"):
        unpack_7z(make_7z(("a.png", PNG), ("b.png", PNG), ("c.png", PNG)))


def test_archives_inside_are_not_opened():
    unpacked = unpack_7z(make_7z(("inner.zip", make_zip(("front.png", PNG))), ("front.png", PNG)))
    assert list(unpacked.pictures) == ["front.png"]
    assert "archive inside the archive" in reasons(unpacked)["inner.zip"]


def test_a_damaged_7z_file():
    with pytest.raises(ArchiveError, match="could not be opened"):
        unpack_7z(b"7z\xbc\xaf\x27\x1c not really")


def test_spreadsheets_in_7z_files_are_kept_apart_from_the_pictures():
    unpacked = unpack_7z(make_7z(("front.png", PNG), ("applications.csv", b"a,b\n" * 20)))
    assert list(unpacked.pictures) == ["front.png"]
    assert [sheet.name for sheet in unpacked.spreadsheets] == ["applications.csv"]


def test_a_batch_can_include_7z_files():
    collected = collect_pictures([("labels.7z", make_7z(("front.png", PNG))), ("back.jpg", JPEG)])
    assert collected.pictures == {"front.png": PNG, "back.jpg": JPEG}


def test_unpacking_7z_writes_nothing_to_disk():
    data = make_7z(("labels/front.png", PNG), ("labels/back.jpg", JPEG))
    unpack_7z(data)  # warm-up: loads any lazy imports
    with watch_disk_writes() as writes:
        assert len(unpack_7z(data).pictures) == 2
    assert list(writes) == []
