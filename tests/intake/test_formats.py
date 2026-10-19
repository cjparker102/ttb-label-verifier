"""HEIC, TIFF, and PDF files. Every file here is made in memory by the test."""

import asyncio
from io import BytesIO

import pytest
from PIL import Image

from app.checking import NotAnImage, TooManyPictures, check_one
from app.intake.images import (
    MAX_PAGES,
    UnreadableFile,
    image_kind,
    shrink_to_jpeg,
    split_pages,
)
from app.rules.application import Application, BeverageType
from tests.disk_watch import watch_disk_writes
from tests.stand_ins import ReplayReader

APPLICATION = Application(
    BeverageType.DISTILLED_SPIRITS, "OLD TOM DISTILLERY", "Bourbon", "45%", "750 mL", "Old Tom"
)


def picture(width=300, height=400, color="white"):
    return Image.new("RGB", (width, height), color)


def saved(image, fmt, **options) -> bytes:
    out = BytesIO()
    image.save(out, format=fmt, **options)
    return out.getvalue()


def multi_page(fmt, pages, size=(300, 400)) -> bytes:
    frames = [
        picture(*size, color)
        for color in ["white", "gray", "black", "red", "blue", "green"][:pages]
    ]
    return saved(frames[0], fmt, save_all=True, append_images=frames[1:])


def test_heic_photos_open_like_any_picture():
    heic = saved(picture(), "HEIF")
    assert image_kind(heic) == "HEIC"
    assert Image.open(BytesIO(shrink_to_jpeg(heic, 1568))).format == "JPEG"


@pytest.mark.parametrize("fmt", ["TIFF", "PDF"])
def test_each_page_becomes_a_picture(fmt):
    pages = split_pages(f"label.{fmt.lower()}", multi_page(fmt, 3))
    assert [name for name, _ in pages] == [f"label.{fmt.lower()}, page {n}" for n in (1, 2, 3)]
    assert all(image_kind(data) == "JPEG" for _, data in pages)


@pytest.mark.parametrize("fmt", ["TIFF", "PDF"])
def test_only_the_first_pages_are_taken(fmt):
    assert len(split_pages("label", multi_page(fmt, 6))) == MAX_PAGES


def test_a_one_page_pdf_keeps_its_name_and_is_drawn_large_enough_to_read():
    small_label = multi_page("PDF", 1, size=(288, 360))  # 4 by 5 inches at 72 points per inch
    [(name, data)] = split_pages("label.pdf", small_label)
    assert name == "label.pdf"
    assert max(Image.open(BytesIO(data)).size) == 2400


def test_other_pictures_pass_through_untouched():
    png = saved(picture(), "PNG")
    assert split_pages("front.png", png) == [("front.png", png)]


def test_a_damaged_pdf_cannot_be_read():
    with pytest.raises(UnreadableFile):
        split_pages("broken.pdf", b"%PDF-1.7 this is not really a PDF")


def test_check_one_reads_every_page_of_a_pdf():
    reader = ReplayReader()
    asyncio.run(check_one(APPLICATION, [("label.pdf", multi_page("PDF", 2))], reader, 1568))
    assert len(reader.received[0]) == 2


def test_too_many_pictures_once_pages_are_counted():
    files = [(f"label{n}.pdf", multi_page("PDF", 3)) for n in range(3)]  # 9 pages
    with pytest.raises(TooManyPictures, match="has 9 pictures"):
        asyncio.run(check_one(APPLICATION, files, ReplayReader(), 1568))


def test_damaged_pdf_is_reported_by_name():
    with pytest.raises(NotAnImage) as raised:
        asyncio.run(
            check_one(APPLICATION, [("broken.pdf", b"%PDF-1.7 junk")], ReplayReader(), 1568)
        )
    assert raised.value.name == "broken.pdf"


def test_picture_bombs_are_refused(monkeypatch):
    # Pillow refuses images more than twice this many pixels; lower it to test that.
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 1000)
    with pytest.raises(NotAnImage):
        asyncio.run(
            check_one(APPLICATION, [("bomb.png", saved(picture(), "PNG"))], ReplayReader(), 1568)
        )


def test_converting_pdf_tiff_and_heic_writes_nothing_to_disk():
    files = {
        "label.pdf": multi_page("PDF", 2),
        "label.tif": multi_page("TIFF", 2),
        "photo.heic": saved(picture(), "HEIF"),
    }

    def convert():
        return [
            shrink_to_jpeg(page, 1568) for n, d in files.items() for _, page in split_pages(n, d)
        ]

    convert()  # warm-up: loads any lazy imports
    with watch_disk_writes() as writes:
        assert len(convert()) == 5
    assert list(writes) == []
