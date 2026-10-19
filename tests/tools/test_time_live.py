from io import BytesIO

from PIL import Image

from tools.make_samples import LABELS_DIR
from tools.time_live import PHONE_WIDTH, phone_photo


def test_a_phone_photo_is_as_wide_and_as_large_as_a_real_one():
    data = phone_photo((LABELS_DIR / "ridgewick-rye-wrong-abv.png").read_bytes())
    picture = Image.open(BytesIO(data))
    assert (picture.format, picture.width) == ("JPEG", PHONE_WIDTH)
    assert len(data) > 3_000_000
