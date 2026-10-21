"""How heavy the warning's heading is, measured by code: a second opinion on the AI
reader's "looks bold".

Bold type has thicker strokes than the same type set normally. Tesseract says where each
word is, so this measures the strokes of the heading's words and of the warning's words
after it, on the same picture. The rules decide what the measurement means.
"""

import io
import statistics
from dataclasses import dataclass

from PIL import Image, ImageFilter

from app.reading.words import Word

SCALE = 4  # each word is enlarged first, so strokes 1 or 2 pixels wide can be measured
BODY_WORDS = 12  # warning words after the heading to measure, at most
MIN_BODY_WORDS = 3
LOOK_AHEAD = 25  # words after the heading to look through for them
# The warning's own words of 3 letters or more, in lower case, so a word from beside the
# warning isn't measured as part of it.
WARNING_WORDS = frozenset(
    "according surgeon general women should not drink alcoholic beverages during pregnancy "
    "because the risk birth defects consumption impairs your ability drive car operate "
    "machinery and may cause health problems".split()
)


@dataclass(frozen=True)
class HeadingWeight:
    ratio: float  # how many times thicker the heading's strokes are than the text's after it
    height: float  # the heading's height in pixels


def key(text: str) -> str:
    return "".join(c for c in text.casefold() if c.isalnum())


def otsu(histogram: list[int]) -> int:
    """The gray level that best splits a picture into ink and background (Otsu's method)."""
    total = sum(histogram)
    weighted = sum(level * count for level, count in enumerate(histogram))
    best, threshold, below, below_weighted = -1.0, 0, 0, 0
    for level, count in enumerate(histogram):
        below += count
        if below == 0:
            continue
        above = total - below
        if above == 0:
            break
        below_weighted += level * count
        spread = below * above * (below_weighted / below - (weighted - below_weighted) / above) ** 2
        if spread > best:
            best, threshold = spread, level
    return threshold


def stroke_width(gray: Image.Image, word: Word) -> float | None:
    """The average stroke width of one word, in pixels: twice its ink's area over its ink's
    edge, which for a stroke of any length is its width. Ink is whichever of dark or light
    covers less of the word's box, so light print on a dark label works too."""
    crop = gray.crop((word.left, word.top, word.left + word.width, word.top + word.height))
    if crop.width < 3 or crop.height < 3:
        return None
    big = crop.resize((crop.width * SCALE, crop.height * SCALE), Image.Resampling.BICUBIC)
    histogram = big.histogram()
    threshold = otsu(histogram)
    dark = sum(histogram[: threshold + 1])
    ink_is_dark = dark <= sum(histogram) - dark
    ink = big.point(lambda level: 255 if (level <= threshold) == ink_is_dark else 0)
    area = ink.histogram()[255]
    edge = area - ink.filter(ImageFilter.MinFilter(3)).histogram()[255]
    if area == 0 or edge <= 0:
        return None
    return 2 * area / edge / SCALE


def heading_and_body(words: list[Word]) -> tuple[list[Word], list[Word]] | None:
    """The heading's words, and the warning's words after it, in one pass of Tesseract's
    words; None if the heading isn't there or too few warning words follow it."""
    keys = [key(word.text) for word in words]
    for i, found in enumerate(keys):
        if found.startswith("governmentwarning"):  # printed without a space
            heading, after = words[i : i + 1], i + 1
        elif found == "government" and i + 1 < len(keys) and keys[i + 1].startswith("warning"):
            heading, after = words[i : i + 2], i + 2
        else:
            continue
        nearby = zip(
            words[after : after + LOOK_AHEAD], keys[after : after + LOOK_AHEAD], strict=True
        )
        body = [word for word, found in nearby if found in WARNING_WORDS][:BODY_WORDS]
        return (heading, body) if len(body) >= MIN_BODY_WORDS else None
    return None


def heading_weight(picture: bytes, passes: list[list[Word]]) -> HeadingWeight | None:
    """The heading's weight against the warning's words after it, from the first of
    Tesseract's passes on this picture that found both; None if none did."""
    gray = Image.open(io.BytesIO(picture)).convert("L")
    for words in passes:
        found = heading_and_body(words)
        if found is None:
            continue
        heading, body = found
        heavy = [w for w in (stroke_width(gray, word) for word in heading) if w]
        light = [w for w in (stroke_width(gray, word) for word in body) if w]
        if heavy and len(light) >= MIN_BODY_WORDS:
            height = statistics.median(word.height for word in heading)
            return HeadingWeight(statistics.median(heavy) / statistics.median(light), height)
    return None
