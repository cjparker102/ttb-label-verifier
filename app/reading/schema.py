"""The JSON contract between the AI reader and the rules.

A reader fills in a LabelReading from the label images alone. It never sees the
application data, and the contract has no field for a verdict: deciding is the
rules' job, not the reader's.
"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Readability(StrEnum):
    CLEAR = "clear"
    UNCLEAR = "unclear"
    NOT_FOUND = "not_found"


class BoldLook(StrEnum):
    YES = "yes"
    NO = "no"
    CANT_TELL = "cant_tell"


class ImageProblem(StrEnum):
    GLARE = "glare"
    BLUR = "blur"
    ANGLE = "angle"
    DARK = "dark"
    TOO_SMALL = "too_small"
    CUT_OFF = "cut_off"


class FieldReading(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str | None = Field(
        description=(
            "The text exactly as printed: same spelling, capitals, punctuation, accents, "
            "and script. Join line breaks with a single space. Null if not found."
        )
    )
    readability: Readability = Field(
        description=(
            "clear: every character is certain. unclear: at least one character is "
            "uncertain. not_found: not on any image."
        )
    )
    image_number: int | None = Field(
        description="Which image the text is on, counting from 1. Null if not found."
    )
    english_meaning: str | None = Field(
        description=(
            "The English meaning if the text is not in English. Null for English text, "
            "and always null for brand names."
        )
    )


class WarningReading(FieldReading):
    heading_bold: BoldLook = Field(description='Whether the words "GOVERNMENT WARNING" look bold.')
    rest_bold: BoldLook = Field(description="Whether the rest of the warning statement looks bold.")


class LabelReading(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brand_name: FieldReading
    class_type: FieldReading = Field(description="The class or type designation.")
    alcohol_content: FieldReading = Field(
        description="The full alcohol content statement, including any proof statement."
    )
    net_contents: FieldReading
    bottler_name_address: FieldReading = Field(
        description=(
            "Each statement naming who bottled, made, or imported the product, with the "
            'company\'s name and address and words such as "Bottled by" or "Imported by".'
        )
    )
    country_of_origin: FieldReading = Field(
        description='The country of origin statement, including words such as "Product of".'
    )
    government_warning: WarningReading = Field(
        description="The full health warning statement, starting with its heading."
    )
    image_problems: list[ImageProblem] = Field(
        description="Problems that make any of the images hard to read. Empty if none."
    )
