import asyncio
from io import BytesIO

from PIL import Image

from app.checking import check_one
from app.photo_coach import TIPS, low_resolution, photo_tips
from app.rules.application import Application, BeverageType
from tests.stand_ins import ReplayReader, recorded_reading

APPLICATION = Application(
    BeverageType.DISTILLED_SPIRITS, "OLD TOM DISTILLERY", "Bourbon", "45%", "750 mL", "Old Tom"
)


def png(width, height):
    out = BytesIO()
    Image.new("RGB", (width, height), "white").save(out, format="PNG")
    return out.getvalue()


def test_one_tip_per_problem_in_a_fixed_order():
    tips = photo_tips(["blur", "glare", "blur", "unknown"])
    assert tips == [TIPS["glare"], TIPS["blur"]]


def test_no_problems_no_tips():
    assert photo_tips([]) == []


def test_low_resolution_is_found_by_code():
    assert low_resolution([png(2000, 1500), png(600, 800)])
    assert not low_resolution([png(2000, 1500)])


def test_the_readers_photo_problems_become_tips_without_changing_results():
    reading = recorded_reading().model_copy(update={"image_problems": ["glare", "angle"]})
    plain = asyncio.run(check_one(APPLICATION, [("a.png", png(2000, 1500))], ReplayReader(), 1568))
    with_glare = asyncio.run(
        check_one(APPLICATION, [("a.png", png(2000, 1500))], ReplayReader(reading), 1568)
    )
    assert with_glare.photo_problems == ("glare", "angle")
    assert [f.status for f in with_glare.result.fields] == [f.status for f in plain.result.fields]


def test_a_small_picture_gets_a_tip_even_with_basic_text_reading():
    outcome = asyncio.run(check_one(APPLICATION, [("small.png", png(600, 800))], None, 1568))
    assert outcome.read_by == "ocr"
    assert "low_resolution" in outcome.photo_problems
