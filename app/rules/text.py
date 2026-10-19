"""Text helpers for comparing what a label says with what an application says."""

import re
import unicodedata

from app.reading.schema import FieldReading, Readability

# Typographic variants that mean the same thing to a reader.
SAME_CHARACTERS = str.maketrans(
    {
        "‘": "'",  # left single quote
        "’": "'",  # right single quote / apostrophe
        "ʼ": "'",  # modifier letter apostrophe
        "“": '"',
        "”": '"',
        "‐": "-",
        "‑": "-",
        "‒": "-",
        "–": "-",
        "—": "-",
        "−": "-",
    }
)

# Unicode name prefixes of non-Latin letters, and the plain name shown to agents.
SCRIPT_NAMES = {
    "HIRAGANA": "Japanese",
    "KATAKANA": "Japanese",
    "CJK": "Chinese or Japanese",
    "HANGUL": "Korean",
    "CYRILLIC": "Cyrillic",
    "GREEK": "Greek",
    "ARABIC": "Arabic",
    "HEBREW": "Hebrew",
    "THAI": "Thai",
    "DEVANAGARI": "Devanagari",
    "GEORGIAN": "Georgian",
    "ARMENIAN": "Armenian",
}


def tidy(text: str) -> str:
    """Unify look-alike characters and collapse runs of whitespace."""
    text = unicodedata.normalize("NFKC", text).translate(SAME_CHARACTERS)
    return re.sub(r"\s+", " ", text).strip()


def is_punctuation(char: str) -> bool:
    return unicodedata.category(char).startswith("P")


def without_punctuation(text: str) -> str:
    """Drop apostrophes, which sit inside words; turn other punctuation into spaces."""
    return "".join(
        ("" if c == "'" else " ") if is_punctuation(c) else c
        for c in text.translate(SAME_CHARACTERS)
    )


def without_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text)
    return unicodedata.normalize(
        "NFC", "".join(c for c in decomposed if not unicodedata.combining(c))
    )


def loose_key(text: str) -> str:
    """Ignore capitals, punctuation, and spacing, but keep accents."""
    return "".join(without_punctuation(tidy(text)).casefold().split())


def cosmetic_differences(a: str, b: str) -> list[str]:
    """Which of capitals, punctuation, and spacing differ between two texts
    that already have the same loose_key."""
    a, b = tidy(a), tidy(b)
    differences = []
    if "".join(without_punctuation(a).split()) != "".join(without_punctuation(b).split()):
        differences.append("capitals")
    if [c for c in a if is_punctuation(c)] != [c for c in b if is_punctuation(c)]:
        differences.append("punctuation")
    if without_punctuation(a).casefold().split() != without_punctuation(b).casefold().split():
        differences.append("spacing")
    return differences


def join_words(words: list[str]) -> str:
    if len(words) <= 2:
        return " and ".join(words)
    return ", ".join(words[:-1]) + ", and " + words[-1]


def non_latin_script(text: str) -> str | None:
    """The plain name of the first non-Latin script used for letters, if any."""
    for char in text:
        if not char.isalpha():
            continue
        name = unicodedata.name(char, "")
        if name.startswith("LATIN"):
            continue
        for prefix, script in SCRIPT_NAMES.items():
            if name.startswith(prefix):
                return script
        return "non-Latin"
    return None


def is_unclear(field: FieldReading) -> bool:
    return field.readability == Readability.UNCLEAR or "[?]" in (field.text or "")


def is_missing(field: FieldReading) -> bool:
    return field.readability == Readability.NOT_FOUND or not (field.text or "").strip()
