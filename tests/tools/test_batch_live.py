"""tools/batch_live.py scores every row of a large batch against its sample."""

from tools.batch_live import tally
from tools.evaluate import load_entries


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
