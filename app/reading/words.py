"""Words Tesseract found on a picture. Kept apart from the readers, so the rules can use
a second reading without importing a reader."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Word:
    """One word Tesseract found, with its box in the picture's pixels."""

    text: str
    left: int
    top: int
    width: int
    height: int


# Tesseract's words on each picture, from each of its layout passes, in reading order.
# A second reading of the label, besides the AI reader's.
Passes = list[list[list[Word]]]
