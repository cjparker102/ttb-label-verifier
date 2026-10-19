from io import BytesIO

from PIL import Image

from app.intake.images import shrink_to_jpeg


def make_image(width, height, mode="RGB", exif_orientation=None, fmt="PNG"):
    image = Image.new(mode, (width, height), "white" if mode == "RGB" else None)
    out = BytesIO()
    if exif_orientation:
        exif = Image.Exif()
        exif[0x0112] = exif_orientation
        image.save(out, format="JPEG", exif=exif.tobytes())
    else:
        image.save(out, format=fmt)
    return out.getvalue()


def open_result(data):
    image = Image.open(BytesIO(data))
    return image.format, image.size


def test_large_image_shrinks_to_max_edge_keeping_shape():
    fmt, size = open_result(shrink_to_jpeg(make_image(2400, 3200), 1568))
    assert fmt == "JPEG"
    assert size == (1176, 1568)


def test_small_image_is_not_enlarged():
    _, size = open_result(shrink_to_jpeg(make_image(800, 600), 1568))
    assert size == (800, 600)


def test_camera_rotation_is_applied():
    # Orientation 6 means the camera was turned; the picture should come out upright.
    _, size = open_result(shrink_to_jpeg(make_image(400, 300, exif_orientation=6), 2000))
    assert size == (300, 400)


def test_transparent_image_becomes_rgb_jpeg():
    data = make_image(100, 100, mode="RGBA")
    result = Image.open(BytesIO(shrink_to_jpeg(data, 2000)))
    assert result.format == "JPEG"
    assert result.mode == "RGB"
