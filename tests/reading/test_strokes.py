"""app/reading/strokes.py: the stroke thickness of the warning's heading against the words
after it, measured on the picture."""

import io

import pytest
from PIL import Image, ImageDraw, ImageFont

from app.highlights import ocr_passes
from app.reading.ocr import tesseract_available
from app.reading.strokes import heading_and_body, heading_weight, stroke_width
from app.reading.words import Word
from tools.make_samples import ROOT

FONTS = ROOT / "tools" / "fonts"
BODY = "(1) ACCORDING TO THE SURGEON GENERAL, WOMEN SHOULD NOT DRINK ALCOHOLIC BEVERAGES"


def font(bold: bool, size: int = 30) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(
        str(FONTS / ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf")), size
    )


def warning_picture(heading_bold: bool, dark_label: bool = False) -> bytes:
    """A warning drawn in two lines: the heading, bold or not, then the body, not bold."""
    ink, paper = ("white", "black") if dark_label else ("black", "white")
    picture = Image.new("RGB", (1500, 140), paper)
    draw = ImageDraw.Draw(picture)
    draw.text((20, 20), "GOVERNMENT WARNING:", font=font(heading_bold), fill=ink)
    draw.text((20, 75), BODY, font=font(False), fill=ink)
    out = io.BytesIO()
    picture.save(out, "JPEG", quality=90)
    return out.getvalue()


def word_box(text: str, bold: bool) -> tuple[Image.Image, Word]:
    picture = Image.new("L", (400, 60), 255)
    ImageDraw.Draw(picture).text((10, 10), text, font=font(bold), fill=0)
    return picture, Word(text, 5, 5, 390, 50)


def test_bold_strokes_measure_thicker_than_regular_ones():
    bold = stroke_width(*word_box("WARNING", bold=True))
    regular = stroke_width(*word_box("WARNING", bold=False))
    assert bold > 1.3 * regular


def test_a_blank_box_has_no_strokes():
    assert stroke_width(Image.new("L", (100, 40), 255), Word("x", 0, 0, 100, 40)) is None
    assert stroke_width(Image.new("L", (100, 40), 255), Word("x", 0, 0, 2, 2)) is None


def words(*texts: str) -> list[Word]:
    return [Word(text, 10 * i, 0, 8, 10) for i, text in enumerate(texts)]


def test_the_heading_and_the_warning_words_after_it_are_found():
    found = heading_and_body(words("Brewed", "GOVERNMENT", "WARNING:", "(1)", "ACCORDING", "TO",
                                   "THE", "SURGEON", "GENERAL,", "LAGER"))  # fmt: skip
    assert found is not None
    heading, body = found
    assert [w.text for w in heading] == ["GOVERNMENT", "WARNING:"]
    # Short words, numbers, and words from beside the warning aren't measured.
    assert [w.text for w in body] == ["ACCORDING", "THE", "SURGEON", "GENERAL,"]


def test_a_heading_printed_without_a_space_is_found():
    found = heading_and_body(words("GOVERNMENTWARNING:", "ACCORDING", "SURGEON", "GENERAL"))
    assert found is not None and [w.text for w in found[0]] == ["GOVERNMENTWARNING:"]


def test_no_heading_or_too_few_warning_words_is_not_measured():
    assert heading_and_body(words("ACCORDING", "TO", "THE", "SURGEON", "GENERAL")) is None
    assert heading_and_body(words("GOVERNMENT", "WARNING", "ACCORDING", "LAGER")) is None


@pytest.mark.skipif(not tesseract_available(), reason="Tesseract is not installed")
@pytest.mark.parametrize("dark_label", [False, True])
def test_a_bold_heading_measures_clearly_heavier_and_a_regular_one_does_not(dark_label):
    bold = warning_picture(heading_bold=True, dark_label=dark_label)
    regular = warning_picture(heading_bold=False, dark_label=dark_label)
    bold_weight = heading_weight(bold, ocr_passes([bold])[0])
    regular_weight = heading_weight(regular, ocr_passes([regular])[0])
    assert bold_weight is not None and regular_weight is not None
    assert bold_weight.ratio > 1.3 and regular_weight.ratio < 1.1
    assert bold_weight.height > 14
