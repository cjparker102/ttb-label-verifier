import pytest
from pydantic import ValidationError

from app.reading.schema import LabelReading, Readability
from app.rules.warning import GOVERNMENT_WARNING


def field(text, readability="clear", image_number=1, english_meaning=None):
    return {
        "text": text,
        "readability": readability,
        "image_number": image_number,
        "english_meaning": english_meaning,
    }


def reading_dict():
    return {
        "brand_name": field("OLD TOM DISTILLERY"),
        "class_type": field("Kentucky Straight Bourbon Whiskey"),
        "alcohol_content": field("45% Alc./Vol. (90 Proof)"),
        "net_contents": field("750 mL"),
        "bottler_name_address": field("Bottled by Old Tom Distillery, Bardstown, Kentucky"),
        "country_of_origin": field(None, readability="not_found", image_number=None),
        "government_warning": {
            **field(GOVERNMENT_WARNING, image_number=2),
            "heading_bold": "yes",
            "rest_bold": "no",
        },
        "image_problems": [],
    }


def test_valid_reading_parses():
    reading = LabelReading.model_validate(reading_dict())
    assert reading.brand_name.text == "OLD TOM DISTILLERY"
    assert reading.country_of_origin.readability is Readability.NOT_FOUND
    assert reading.government_warning.image_number == 2


def test_reading_has_no_place_for_a_verdict():
    data = reading_dict()
    data["all_fields_pass"] = True
    with pytest.raises(ValidationError):
        LabelReading.model_validate(data)


def test_field_rejects_extra_keys():
    data = reading_dict()
    data["brand_name"]["result"] = "pass"
    with pytest.raises(ValidationError):
        LabelReading.model_validate(data)


def test_unknown_readability_is_rejected():
    data = reading_dict()
    data["net_contents"]["readability"] = "probably"
    with pytest.raises(ValidationError):
        LabelReading.model_validate(data)


def test_missing_field_is_rejected():
    data = reading_dict()
    del data["government_warning"]
    with pytest.raises(ValidationError):
        LabelReading.model_validate(data)


def test_every_object_in_the_json_schema_forbids_extra_keys():
    # Structured outputs need additionalProperties: false on every object.
    schema = LabelReading.model_json_schema()
    objects = [schema, *schema["$defs"].values()]
    objects = [o for o in objects if o.get("type") == "object"]
    assert objects
    for obj in objects:
        assert obj.get("additionalProperties") is False, obj.get("title")
