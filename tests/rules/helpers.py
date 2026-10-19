"""Builders for readings used as test inputs."""

from app.reading.schema import FieldReading, WarningReading


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


def read_warning(text, heading_bold="yes", rest_bold="no", readability=None):
    """The warning as the reader would return it. No text means not found."""
    field = read(text, readability)
    return WarningReading(**field.model_dump(), heading_bold=heading_bold, rest_bold=rest_bold)
