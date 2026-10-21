"""tools/batch_live.py scores every row of a large batch against its sample."""

import io
import zipfile

from PIL import Image

from tools.batch_live import own_pictures, tally
from tools.evaluate import load_entries, spreadsheet


def test_rows_are_scored_against_their_samples_and_misses_named():
    samples = load_entries(["old-tom-bourbon", "tidewick-pale-ale--far"])
    rows = [samples[0], samples[1], samples[0]]
    expected = [
        {k: v if isinstance(v, str) else v[0] for k, v in s["expected"].items()} for s in samples
    ]
    wrong = dict(expected[0], brand_name="fail")  # a false Problem on the third row
    by_row = {
        2: {"read_by": "AI reader", "got": expected[0]},
        3: {"read_by": "AI reader", "got": dict(expected[1], government_warning="review")},
        4: {"read_by": "Basic text reading", "got": wrong},
    }
    judged, read_by, as_expected, misses = tally(rows, by_row)
    assert as_expected == 2  # Check this on a photo-like label is acceptable
    assert read_by == {"AI reader": 2, "Basic text reading": 1}
    assert misses == {"old-tom-bourbon: brand_name false fail": 1}


def test_each_row_can_have_its_own_pictures_about_the_size_asked_for():
    by_id = {s["id"]: s for s in load_entries(["stones-throw-gin", "old-tom-bourbon"])}
    gin, bourbon = by_id["stones-throw-gin"], by_id["old-tom-bourbon"]  # 1 and 2 pictures
    rows, upload = own_pictures([gin, bourbon, gin], megabytes=0.9)
    assert [row["images"] for row in rows] == [
        ["row-002-stones-throw-gin.jpg"],
        ["row-003-old-tom-bourbon_front.jpg", "row-003-old-tom-bourbon_back.jpg"],
        ["row-004-stones-throw-gin.jpg"],
    ]
    with zipfile.ZipFile(io.BytesIO(upload)) as archive:
        sizes = {info.filename: info.file_size for info in archive.infolist()}
        assert Image.open(io.BytesIO(archive.read("row-004-stones-throw-gin.jpg"))).size == (
            2400,
            3200,
        )
        # The same sample in two rows gives two different files, as two photos would.
        assert archive.read("row-002-stones-throw-gin.jpg") != archive.read(
            "row-004-stones-throw-gin.jpg"
        )
    assert set(sizes) == {name for row in rows for name in row["images"]}
    assert 0.8e6 < sizes["row-002-stones-throw-gin.jpg"] <= 0.9e6  # one picture, the whole size
    assert 0.35e6 < sizes["row-003-old-tom-bourbon_front.jpg"] <= 0.45e6  # two share it
    assert b"row-003-old-tom-bourbon_front.jpg; row-003-old-tom-bourbon_back.jpg" in spreadsheet(
        rows
    )
