"""Prepares label images for reading. Everything happens in memory."""

from io import BytesIO

import pypdfium2
from PIL import Image, ImageOps, ImageSequence
from pillow_heif import register_heif_opener

register_heif_opener()  # lets Pillow open HEIC photos from iPhones

FORMATS = "JPEG, PNG, WebP, GIF, HEIC, TIFF, or PDF"  # in plain words, for messages
ACCEPT = (  # for the browser's file picker
    "image/jpeg,image/png,image/webp,image/gif,image/heic,image/heif,.heic,.heif,"
    "image/tiff,.tif,.tiff,application/pdf,.pdf"
)
MAX_PAGES = 4  # pictures taken from one PDF or multi-page TIFF
PDF_LONG_EDGE = 2400  # label PDFs are often a few inches across; draw them this big


class UnreadableFile(ValueError):
    """A file that looks like a picture format but can't be opened."""


def shrink_to_jpeg(data: bytes, max_edge: int, quality: int = 90) -> bytes:
    """Return the image as a JPEG whose longer side is at most max_edge pixels.

    Applies the camera's rotation tag first, so photos read the right way up.
    Never enlarges a smaller image.
    """
    with Image.open(BytesIO(data)) as image:
        image = ImageOps.exif_transpose(image)
        if image.mode != "RGB":
            image = flatten_to_rgb(image)
        image.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
        out = BytesIO()
        image.save(out, format="JPEG", quality=quality)
    return out.getvalue()


def flatten_to_rgb(image: Image.Image) -> Image.Image:
    """Convert to RGB, putting any transparent areas on a white background."""
    rgba = image.convert("RGBA")
    background = Image.new("RGB", rgba.size, "white")
    background.paste(rgba, mask=rgba.getchannel("A"))
    return background


def as_jpeg(image: Image.Image) -> bytes:
    if image.mode != "RGB":
        image = flatten_to_rgb(image)
    out = BytesIO()
    image.save(out, format="JPEG", quality=95)
    return out.getvalue()


def pdf_pages(data: bytes) -> list[bytes]:
    try:
        document = pypdfium2.PdfDocument(data)
    except pypdfium2.PdfiumError as error:
        raise UnreadableFile("damaged or password-protected PDF") from error
    try:
        pages = []
        for index in range(min(len(document), MAX_PAGES)):
            page = document[index]
            width, height = page.get_size()  # in points, 72 to the inch
            scale = min(10.0, PDF_LONG_EDGE / max(width, height, 1))
            pages.append(as_jpeg(page.render(scale=scale).to_pil()))
            page.close()
        return pages
    finally:
        document.close()


def tiff_pages(data: bytes) -> list[bytes]:
    with Image.open(BytesIO(data)) as image:
        frames = list(ImageSequence.Iterator(image))[:MAX_PAGES]
        return [as_jpeg(frame.copy()) for frame in frames]


def split_pages(name: str, data: bytes) -> list[tuple[str, bytes]]:
    """One picture per page for PDFs and multi-page TIFFs; other pictures pass through."""
    kind = image_kind(data)
    if kind == "PDF":
        pages = pdf_pages(data)
    elif kind == "TIFF":
        pages = tiff_pages(data)
    else:
        return [(name, data)]
    if len(pages) == 1:
        return [(name, pages[0])]
    return [(f"{name}, page {number}", page) for number, page in enumerate(pages, start=1)]


# The first bytes of each picture format the app accepts.
SIGNATURES = {
    b"\xff\xd8\xff": "JPEG",
    b"\x89PNG\r\n\x1a\n": "PNG",
    b"GIF87a": "GIF",
    b"GIF89a": "GIF",
    b"II*\x00": "TIFF",
    b"MM\x00*": "TIFF",
    b"%PDF-": "PDF",
}
HEIF_BRANDS = {b"heic", b"heix", b"hevc", b"hevx", b"heim", b"heis", b"mif1", b"msf1"}


def image_kind(data: bytes) -> str | None:
    """The picture format, judged by the file's content rather than its name."""
    for signature, kind in SIGNATURES.items():
        if data.startswith(signature):
            return kind
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "WebP"
    if data[4:8] == b"ftyp" and data[8:12] in HEIF_BRANDS:
        return "HEIC"
    return None
