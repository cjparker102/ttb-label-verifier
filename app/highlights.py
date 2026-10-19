"""Where each field to look at is on the label picture, so the page can outline it.

The AI reader says which picture a field is on, but not where. Tesseract reports each
word it finds with its position, so code looks for the reading of the field among those
words. When nothing is close enough, the field isn't outlined. An outline only points
the way; it never changes a result.
"""

from dataclasses import dataclass
from difflib import SequenceMatcher

from app.reading.ocr import Word, ocr_words
from app.rules.results import Status
from app.rules.verdict import LabelResult

MATCH = 0.8  # how close the words must be to the reading to count as found
PADDING = 16  # pixels around the words, so the outline doesn't cover them
OUTLINED = (Status.FAIL, Status.REVIEW)


@dataclass(frozen=True)
class Highlight:
    field: str
    title: str
    status: Status
    image_number: int  # 1-based, as in the reading
    left: int
    top: int
    width: int
    height: int


def words_on(pictures: list[bytes]) -> list[list[Word]]:
    """Each picture's words, from two Tesseract passes: the usual layout, which copes
    better with a tilted photo, and "sparse text", which finds short lines standing
    alone. Duplicates don't matter, because find_highlights takes words by area."""
    return [ocr_words(p, layout="3") + ocr_words(p, layout="11") for p in pictures]


def key(text: str) -> str:
    """A word reduced to its letters and digits, in lower case."""
    return "".join(c for c in text.casefold() if c.isalnum())


def locate(text: str, words: list[Word], taken: set[int]) -> range | None:
    """The run of words that best matches `text`, leaving out words already taken by
    another field, or None if nothing is close enough. Ties go to the earlier run."""
    wanted = " ".join(k for k in map(key, text.split()) if k)
    count = len(wanted.split())
    if not count:
        return None
    keys = [key(word.text) for word in words]
    best, best_score = None, 0.0
    for size in range(max(1, count - 2), count + 3):
        for start in range(len(words) - size + 1):
            span = range(start, start + size)
            if not keys[start] or not keys[span[-1]] or taken.intersection(span):
                continue  # runs start and end on a real word
            matcher = SequenceMatcher(None, " ".join(keys[i] for i in span if keys[i]), wanted)
            # The quick ratios are upper bounds of the real one, and far cheaper.
            bar = max(best_score, MATCH)
            if matcher.real_quick_ratio() < bar or matcher.quick_ratio() < bar:
                continue
            score = matcher.ratio()
            if score > best_score:
                best, best_score = span, score
    return best if best_score >= MATCH else None


def box(words: list[Word], span: range) -> tuple[int, int, int, int]:
    """The box around a run of words, padded: left, top, width, height."""
    chosen = [words[i] for i in span]
    left = max(0, min(w.left for w in chosen) - PADDING)
    top = max(0, min(w.top for w in chosen) - PADDING)
    right = max(w.left + w.width for w in chosen) + PADDING
    bottom = max(w.top + w.height for w in chosen) + PADDING
    return left, top, right - left, bottom - top


def inside(word: Word, area: tuple[int, int, int, int]) -> bool:
    left, top, width, height = area
    x, y = word.left + word.width / 2, word.top + word.height / 2
    return left <= x <= left + width and top <= y <= top + height


def find_highlights(result: LabelResult, words_by_image: list[list[Word]]) -> list[Highlight]:
    """Outlines for the fields to look at, in the page's field order.

    Every field with text is located, longest first, and then every word inside its
    outline is taken. So a short field, such as a brand, can't be "found" inside a
    longer one, such as the bottler's company name. A picture's words can come from
    more than one Tesseract pass; taking words by area covers each pass's copy."""
    taken: dict[int, set[int]] = {}
    found: dict[str, Highlight] = {}
    fields = [f for f in result.fields if f.label_says and f.image_number]
    for field in sorted(fields, key=lambda f: len(f.label_says or ""), reverse=True):
        index = field.image_number - 1
        if not 0 <= index < len(words_by_image):
            continue
        words = words_by_image[index]
        span = locate(field.label_says or "", words, taken.setdefault(index, set()))
        if span is None:
            continue
        area = box(words, span)
        taken[index].update(i for i, word in enumerate(words) if inside(word, area))
        if field.status in OUTLINED:
            found[field.field] = Highlight(
                field.field, field.title, field.status, field.image_number, *area
            )
    return [found[f.field] for f in result.fields if f.field in found]
