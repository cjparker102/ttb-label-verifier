"""Builders for readings used as test inputs."""

from app.reading.schema import FieldReading


def read(text, readability=None, image_number=1, english_meaning=None):
    """A field as the reader would return it. No text means not found."""
    if readability is None:
        readability = "clear" if text is not None else "not_found"
    return FieldReading(
        text=text,
        readability=readability,
        image_number=image_number if text is not None else None,
        english_meaning=english_meaning,
    )
