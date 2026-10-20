from io import BytesIO

from PIL import Image

from tools.make_samples import LABELS_DIR
from tools.time_live import PHONE_WIDTH, phone_photo, summary


def test_a_phone_photo_is_as_wide_and_as_large_as_a_real_one():
    data = phone_photo((LABELS_DIR / "ridgewick-rye-wrong-abv.png").read_bytes())
    picture = Image.open(BytesIO(data))
    assert (picture.format, picture.width) == ("JPEG", PHONE_WIDTH)
    assert len(data) > 3_000_000


def test_the_summary_gives_the_median_p95_and_slowest():
    times = [2.0] * 18 + [4.4, 8.8]
    # p95 is the 19th of 20 times: a time that was really measured.
    assert summary(times) == "median 2.00 s, p95 4.40 s, slowest 8.80 s"
