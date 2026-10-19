"""Prepares label images for reading. Everything happens in memory."""

from io import BytesIO

from PIL import Image, ImageOps


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
