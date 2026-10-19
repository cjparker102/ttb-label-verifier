"""Archive safety. Every archive here is built in memory by the test itself."""

import io
import stat
import zipfile

import pytest

from app.intake import archives
from app.intake.archives import ArchiveError, unpack_zip
from app.intake.images import image_kind
from app.intake.matching import match_rows
from app.intake.spreadsheet import ApplicationRow

PNG = b"\x89PNG\r\n\x1a\n" + b"picture data " * 50
JPEG = b"\xff\xd8\xff\xe0" + b"picture data " * 50


def make_zip(*entries) -> bytes:
    """Entries are (name, data) pairs, or ZipInfo objects paired with data."""
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in entries:
            archive.writestr(name, data)
    return out.getvalue()


def reasons(unpacked):
    return {s.name: s.reason for s in unpacked.skipped}


def test_pictures_come_out_by_file_name_without_folders():
    unpacked = unpack_zip(make_zip(("labels/front.png", PNG), ("labels/back.jpg", JPEG)))
    assert unpacked.pictures == {"front.png": PNG, "back.jpg": JPEG}
    assert unpacked.skipped == []


def test_system_clutter_is_skipped_and_listed():
    unpacked = unpack_zip(
        make_zip(("front.png", PNG), ("__MACOSX/._front.png", b"x"), (".DS_Store", b"x"))
    )
    assert list(unpacked.pictures) == ["front.png"]
    assert set(reasons(unpacked)) == {"__MACOSX/._front.png", ".DS_Store"}


def test_files_that_are_not_pictures_are_judged_by_content():
    unpacked = unpack_zip(make_zip(("notes.png", b"just some text"), ("real.dat", PNG)))
    assert list(unpacked.pictures) == ["real.dat"]
    assert "Not a picture or PDF this app can read" in reasons(unpacked)["notes.png"]


@pytest.mark.parametrize("name", ["../../etc/evil.png", "/abs/evil.png", "C:\\evil.png"])
def test_zip_slip_paths_are_refused(name):
    unpacked = unpack_zip(make_zip((name, PNG)))
    assert unpacked.pictures == {}
    assert "points outside the archive" in reasons(unpacked)[name]


def test_nested_archives_are_not_opened():
    inner = make_zip(("front.png", PNG))
    unpacked = unpack_zip(make_zip(("inner.zip", inner), ("disguised.png", inner)))
    assert unpacked.pictures == {}
    assert all("archive inside the archive" in r for r in reasons(unpacked).values())


def mark_encrypted(data: bytes) -> bytes:
    """Set the "encrypted" bit the way a password-protected ZIP has it. Python's zipfile
    can't write encrypted entries, and clears this bit if asked to."""
    data = bytearray(data)
    local = data.index(b"PK\x03\x04")  # file header: flags at offset 6
    central = data.index(b"PK\x01\x02")  # directory entry: flags at offset 8
    data[local + 6] |= 0x1
    data[central + 8] |= 0x1
    return bytes(data)


def test_password_protected_entries_are_skipped():
    unpacked = unpack_zip(mark_encrypted(make_zip(("secret.png", PNG))))
    assert unpacked.pictures == {}
    assert "Password-protected" in reasons(unpacked)["secret.png"]


def test_links_are_skipped():
    info = zipfile.ZipInfo("link.png")
    info.external_attr = (stat.S_IFLNK | 0o777) << 16
    unpacked = unpack_zip(make_zip((info, "front.png")))
    assert "A link" in reasons(unpacked)["link.png"]


def test_zip_bomb_entries_are_not_unpacked():
    unpacked = unpack_zip(make_zip(("bomb.png", b"\0" * (2 * 1024 * 1024))))
    assert unpacked.pictures == {}
    assert "Packed far more tightly" in reasons(unpacked)["bomb.png"]


def test_oversized_pictures_are_skipped(monkeypatch):
    monkeypatch.setattr(archives, "MAX_PICTURE_BYTES", 100)
    unpacked = unpack_zip(make_zip(("big.png", PNG)))
    assert "Larger than" in reasons(unpacked)["big.png"]


def test_total_unpacked_size_is_capped(monkeypatch):
    monkeypatch.setattr(archives, "MAX_TOTAL_BYTES", len(PNG) + 10)
    with pytest.raises(ArchiveError, match="larger than"):
        unpack_zip(make_zip(("a.png", PNG), ("b.png", PNG)))


def test_too_many_items(monkeypatch):
    monkeypatch.setattr(archives, "MAX_ITEMS", 2)
    with pytest.raises(ArchiveError, match="holds 3 items"):
        unpack_zip(make_zip(("a.png", PNG), ("b.png", PNG), ("c.png", PNG)))


def test_too_many_pictures(monkeypatch):
    monkeypatch.setattr(archives, "MAX_PICTURES", 1)
    with pytest.raises(ArchiveError, match="more than 1 pictures"):
        unpack_zip(make_zip(("a.png", PNG), ("b.png", PNG)))


def test_two_pictures_with_the_same_name_in_different_folders():
    unpacked = unpack_zip(make_zip(("set1/front.png", PNG), ("set2/FRONT.png", JPEG)))
    assert unpacked.pictures == {"front.png": PNG}
    assert "Another picture is also named" in reasons(unpacked)["set2/FRONT.png"]


def test_something_that_is_not_a_zip():
    with pytest.raises(ArchiveError, match="could not be opened"):
        unpack_zip(b"definitely not a zip")


@pytest.mark.parametrize(
    ("data", "kind"),
    [
        (PNG, "PNG"),
        (JPEG, "JPEG"),
        (b"GIF89a....", "GIF"),
        (b"RIFF\x00\x00\x00\x00WEBPVP8 ", "WebP"),
        (b"%PDF-1.7", "PDF"),
        (b"II*\x00rest", "TIFF"),
        (b"\x00\x00\x00\x18ftypheic", "HEIC"),
        (b"plain text", None),
        (b"", None),
    ],
)
def test_image_kind_reads_the_first_bytes(data, kind):
    assert image_kind(data) == kind


def row(number, *file_names):
    return ApplicationRow(number, file_names, None, ())


def test_rows_are_matched_to_pictures_ignoring_folders_and_capitals():
    pictures = {"Front.PNG": PNG, "back.jpg": JPEG, "extra.png": PNG}
    matched, unused = match_rows(
        [row(2, "labels/front.png", "back.jpg"), row(3, "gone.png")], pictures
    )
    assert [name for name, _ in matched[0].pictures] == ["Front.PNG", "back.jpg"]
    assert matched[0].missing == ()
    assert matched[1].pictures == ()
    assert matched[1].missing == ("gone.png",)
    assert unused == ["extra.png"]


def test_a_batch_can_mix_loose_pictures_and_zip_files():
    from app.intake.archives import collect_pictures

    files = [
        ("front.png", PNG),
        ("more.zip", make_zip(("back.jpg", JPEG), ("FRONT.png", PNG))),
        ("notes.txt", b"hello"),
    ]
    collected = collect_pictures(files)
    assert collected.pictures == {"front.png": PNG, "back.jpg": JPEG}
    found = {s.name: s.reason for s in collected.skipped}
    assert "Another picture is also named" in found["more.zip: FRONT.png"]
    assert "Not a picture this app can read" in found["notes.txt"]


def test_a_batch_is_capped_at_the_picture_limit(monkeypatch):
    from app.intake.archives import collect_pictures

    monkeypatch.setattr(archives, "MAX_PICTURES", 1)
    with pytest.raises(ArchiveError, match="more than 1 pictures"):
        collect_pictures([("a.png", PNG), ("b.png", PNG)])


def test_a_damaged_zip_in_a_batch_says_so():
    from app.intake.archives import collect_pictures

    with pytest.raises(ArchiveError, match="could not be opened"):
        collect_pictures([("labels.zip", b"not a zip")])
