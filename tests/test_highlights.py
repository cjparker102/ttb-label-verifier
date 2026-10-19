"""Outlining the fields to look at on the label picture."""

import asyncio
import json
import time
from io import BytesIO

import pytest
from PIL import Image

from app.checking import check_one
from app.highlights import PADDING, box, find_highlights, locate, words_on
from app.intake.images import shrink_to_jpeg
from app.reading.ocr import OcrFailed, Word, ocr_text, ocr_words, tesseract_available
from app.rules.results import Check, Status
from app.rules.verdict import FieldResult, LabelResult
from tests.stand_ins import PerfectReader
from tools.evaluate import application_for
from tools.make_samples import LABELS_DIR, SAMPLES_DIR

needs_tesseract = pytest.mark.skipif(not tesseract_available(), reason="Tesseract is not installed")
EXPECTED = {e["id"]: e for e in json.loads((SAMPLES_DIR / "expected.json").read_text("utf-8"))}


def line(text: str, top: int, left: int = 100) -> list[Word]:
    """Words laid out left to right on one line, 20 pixels apart."""
    words = []
    for token in text.split():
        words.append(Word(token, left, top, 10 * len(token), 30))
        left += 10 * len(token) + 20
    return words


def field(name: str, label_says: str | None, status: Status, image_number: int = 1):
    return FieldResult(
        field=name,
        title=name.replace("_", " ").capitalize(),
        application_says="",
        label_says=label_says,
        image_number=image_number if label_says else None,
        checks=(Check(status, "Reason."),),
    )


LABEL = (
    line("RIDGEWICK", 100)
    + line("Straight Rye Whisky", 200)
    + line("46% Alc./Vol. (92 Proof)", 300)
    + line("750 mL", 400)
    + line("Bottled by Ridgewick Spirits Co., Lexington, Kentucky", 500)
)


def test_locate_finds_the_run_of_words_that_matches():
    span = locate("46% Alc./Vol. (92 Proof)", LABEL, set())
    assert [LABEL[i].text for i in span] == ["46%", "Alc./Vol.", "(92", "Proof)"]


def test_locate_ignores_capitals_and_punctuation():
    span = locate("bottled by ridgewick spirits co lexington kentucky", LABEL, set())
    assert LABEL[span[0]].text == "Bottled" and LABEL[span[-1]].text == "Kentucky"


def test_locate_allows_a_small_misreading():
    misread = line("46% A1c./Vol. (92 Pro0f)", 300)
    assert locate("46% Alc./Vol. (92 Proof)", misread, set()) is not None


def test_locate_gives_up_when_nothing_is_close():
    assert locate("45% Alc./Vol. (90 Proof)", line("Straight Rye Whisky", 0), set()) is None
    assert locate("...", LABEL, set()) is None  # no letters or digits to look for


def test_locate_skips_words_already_taken():
    taken = set(range(len(LABEL) - 7, len(LABEL)))  # the bottler line
    span = locate("Ridgewick", LABEL, taken)
    assert span == range(0, 1)
    assert locate("Lexington", LABEL, taken) is None


def test_ties_go_to_the_earlier_run():
    words = line("750 mL", 100) + line("750 mL", 400)
    assert locate("750 mL", words, set()) == range(0, 2)


def test_a_run_never_starts_or_ends_on_a_stray_mark():
    words = line("— 750 mL |", 100)
    span = locate("750 mL", words, set())
    assert [words[i].text for i in span] == ["750", "mL"]


def test_box_is_padded_but_stays_on_the_picture():
    words = [Word("A", 5, 3, 10, 20), Word("B", 30, 8, 10, 20)]
    assert box(words, range(2)) == (0, 0, 40 + PADDING, 28 + PADDING)
    far = [Word("A", 100, 200, 10, 20)]
    assert box(far, range(1)) == (100 - PADDING, 200 - PADDING, 10 + 2 * PADDING, 20 + 2 * PADDING)


def test_only_fields_to_look_at_are_outlined_in_page_order():
    result = LabelResult(
        (
            field("brand_name", "RIDGEWICK", Status.PASS),
            field("alcohol_content", "46% Alc./Vol. (92 Proof)", Status.FAIL),
            field("net_contents", "750 mL", Status.REVIEW),
            field("country_of_origin", None, Status.NOT_NEEDED),
        )
    )
    highlights = find_highlights(result, [LABEL])
    assert [(h.field, h.status) for h in highlights] == [
        ("alcohol_content", Status.FAIL),
        ("net_contents", Status.REVIEW),
    ]
    alcohol = highlights[0]
    assert (alcohol.image_number, alcohol.title) == (1, "Alcohol content")
    assert alcohol.top == 300 - PADDING


def test_a_brand_is_not_found_inside_the_bottlers_name():
    # Tesseract missed the brand line, but the brand is also part of the company name.
    words = [w for w in LABEL if w.top != 100]
    result = LabelResult(
        (
            field("brand_name", "RIDGEWICK", Status.REVIEW),
            field(
                "bottler_name_address",
                "Bottled by Ridgewick Spirits Co., Lexington, Kentucky",
                Status.PASS,
            ),
        )
    )
    assert find_highlights(result, [words]) == []


def test_words_from_a_second_pass_are_taken_too():
    # Two Tesseract passes see the same line, so its words appear twice.
    bottler = line("Bottled by Ridgewick Spirits Co., Lexington, Kentucky", 500)
    result = LabelResult(
        (
            field("brand_name", "RIDGEWICK", Status.REVIEW),
            field("bottler_name_address", " ".join(w.text for w in bottler), Status.PASS),
        )
    )
    assert find_highlights(result, [bottler + bottler]) == []


def test_a_picture_number_the_reader_got_wrong_is_ignored():
    result = LabelResult((field("net_contents", "750 mL", Status.FAIL, image_number=3),))
    assert find_highlights(result, [LABEL]) == []


# With the real Tesseract


def sample_picture(name: str) -> bytes:
    return shrink_to_jpeg((LABELS_DIR / name).read_bytes(), 1568)


@needs_tesseract
def test_ocr_words_gives_each_word_with_its_place():
    picture = sample_picture("ridgewick-rye-wrong-abv.png")
    words = ocr_words(picture)
    width, height = Image.open(BytesIO(picture)).size
    brand = next(w for w in words if w.text == "RIDGEWICK")
    assert 0 <= brand.left < brand.left + brand.width <= width
    assert 0 <= brand.top < brand.top + brand.height <= height


@needs_tesseract
def test_both_passes_find_a_short_line_standing_alone():
    # The usual layout can skip a short line like "90 Proof"; the sparse-text pass finds it.
    words = words_on([sample_picture("irongate-bourbon-proof-only.png")])[0]
    assert locate("90 Proof", words, set()) is not None


@needs_tesseract
@pytest.mark.parametrize(
    ("sample_id", "field_name", "printed"),
    [
        ("ridgewick-rye-wrong-abv", "alcohol_content", "46%"),
        ("granitefall-bourbon-prompt-injection", "alcohol_content", "47%"),
        ("saltreed-vodka-net-contents", "net_contents", "700"),
        ("ridgewick-rye-wrong-abv--angled", "alcohol_content", "46%"),
    ],
)
def test_the_outline_surrounds_the_problem_on_a_real_sample(sample_id, field_name, printed):
    entry = EXPECTED[sample_id]
    images = [(name, (LABELS_DIR / name).read_bytes()) for name in entry["images"]]
    reader = PerfectReader([entry["truth"]])
    outcome = asyncio.run(check_one(application_for(entry), images, reader, 1568, outline=True))
    [highlight] = outcome.highlights
    assert highlight.field == field_name
    # Read what is inside the outline: it is the problem, not some other line.
    picture = Image.open(BytesIO(outcome.images[highlight.image_number - 1]))
    crop = picture.crop(
        (
            highlight.left,
            highlight.top,
            highlight.left + highlight.width,
            highlight.top + highlight.height,
        )
    )
    out = BytesIO()
    crop.save(out, format="JPEG")
    assert printed in ocr_text(out.getvalue(), 60, "7")  # layout 7: a single line


def test_no_outlines_unless_asked():
    entry = EXPECTED["ridgewick-rye-wrong-abv"]
    images = [(name, (LABELS_DIR / name).read_bytes()) for name in entry["images"]]
    outcome = asyncio.run(
        check_one(application_for(entry), images, PerfectReader([entry["truth"]]), 1568)
    )
    assert outcome.highlights == ()


@needs_tesseract
@pytest.mark.parametrize("failure", [OcrFailed("tesseract exited with 1"), ValueError("bug")])
def test_a_failure_while_outlining_never_stops_the_check(monkeypatch, failure):
    def fail(pictures):
        raise failure

    monkeypatch.setattr("app.checking.words_on", fail)
    entry = EXPECTED["ridgewick-rye-wrong-abv"]
    images = [(name, (LABELS_DIR / name).read_bytes()) for name in entry["images"]]
    outcome = asyncio.run(
        check_one(
            application_for(entry), images, PerfectReader([entry["truth"]]), 1568, outline=True
        )
    )
    assert outcome.result.status == Status.FAIL
    assert outcome.highlights == ()


@needs_tesseract
def test_a_check_never_waits_long_for_outlines(monkeypatch):
    def slow(pictures):
        time.sleep(1.5)
        return [[] for _ in pictures]

    monkeypatch.setattr("app.checking.words_on", slow)
    monkeypatch.setattr("app.checking.OUTLINE_WAIT", 0.05)
    entry = EXPECTED["ridgewick-rye-wrong-abv"]
    images = [(name, (LABELS_DIR / name).read_bytes()) for name in entry["images"]]
    outcome = asyncio.run(
        check_one(
            application_for(entry), images, PerfectReader([entry["truth"]]), 1568, outline=True
        )
    )
    assert outcome.result.status == Status.FAIL
    assert outcome.highlights == ()
    assert outcome.seconds < 1.2  # without the limit it would be over 1.5
