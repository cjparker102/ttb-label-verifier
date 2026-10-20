import pytest

from app.reading.schema import LabelReading
from app.reading.words import Word
from app.rules.names import check_bottler, check_brand, check_class, check_name, statements
from app.rules.results import Status
from app.rules.warning import GOVERNMENT_WARNING
from tests.rules.helpers import read, read_warning


@pytest.mark.parametrize(
    ("application", "label", "status", "note"),
    [
        ("OLD TOM DISTILLERY", "OLD TOM DISTILLERY", Status.PASS, None),
        # Typographic apostrophe and extra spaces are not real differences.
        ("Stone's Throw", "Stone’s  Throw", Status.PASS, None),
        ("Stone's Throw", "STONE'S THROW", Status.PASS, "Matches, different capitals"),
        ("Stone's Throw", "Stones Throw", Status.PASS, "Matches, different punctuation"),
        ("Old Tom", "OLDTOM", Status.PASS, "Matches, different capitals and spacing"),
        ("Chateau Landrevin", "CHÂTEAU LANDREVIN", Status.REVIEW, None),
        ("Rose", "Rosé", Status.REVIEW, None),
        ("Dassai", "獺祭", Status.REVIEW, None),
        ("Stone's Throw", "Stone's Toss", Status.FAIL, None),
        ("Vodka", "Gin", Status.FAIL, None),
    ],
)
def test_name_matching(application, label, status, note):
    result = check_name("brand name", application, read(label))
    assert result.status == status
    assert result.note == note


def test_capitals_note_reason_names_both_values():
    result = check_name("brand name", "Stone's Throw", read("STONE'S THROW"))
    assert result.reason == (
        'The label says "STONE\'S THROW" and the application says "Stone\'s Throw". '
        "Only the capitals differ."
    )


def test_non_latin_reason_names_the_script():
    result = check_name("brand name", "Dassai", read("獺祭"))
    assert "Chinese or Japanese script" in result.reason
    assert check_name("brand name", "Soju One", read("소주 원")).reason.count("Korean") == 1


def test_missing_from_label_fails():
    result = check_name("brand name", "OLD TOM DISTILLERY", read(None))
    assert result.status == Status.FAIL
    assert result.reason == "The label doesn't show the brand name."


@pytest.mark.parametrize(
    "label",
    [read("OLD TOM DISTILLERY", readability="unclear"), read("OLD T[?]M DISTILLERY")],
)
def test_hard_to_read_needs_review_even_if_it_matches(label):
    assert check_name("brand name", "OLD TOM DISTILLERY", label).status == Status.REVIEW


def test_blank_application_needs_review():
    assert check_name("class or type", "", read("Vodka")).status == Status.REVIEW


@pytest.mark.parametrize(
    ("application", "label", "status"),
    [
        (
            "Old Tom Distillery, Bardstown, Kentucky",
            "Bottled by Old Tom Distillery, Bardstown, Kentucky",
            Status.PASS,
        ),
        (
            "Stone's Throw Spirits, Portland, Oregon",
            "Distilled and bottled by Stone's Throw Spirits, Portland, Oregon",
            Status.PASS,
        ),
        (
            "Tidewick Brewing Co., Norfolk, Virginia",
            "Brewed and canned by Tidewick Brewing Co., Norfolk, Virginia",
            Status.PASS,
        ),
        (
            "Landrevin Imports, New York, NY",
            "Imported by Landrevin Imports, New York, NY",
            Status.PASS,
        ),
        (
            "Old Tom Distillery, Bardstown, Kentucky",
            "Bottled by Old Tom Distillery, Bardstown, KY",
            Status.PASS,
        ),
        (
            "Old Tom Distillery, Bardstown, Kentucky",
            "Bottled by Ridgewick Spirits Co., Lexington, Kentucky",
            Status.FAIL,
        ),
    ],
)
def test_bottler_matching(application, label, status):
    assert check_bottler(application, read(label)).status == status


def test_bottler_name_containing_by_is_not_cut():
    # "by" only counts as a lead-in when it is a whole word after a few words.
    result = check_bottler(
        "Derby Distillers, Louisville, Kentucky", read("Derby Distillers, Louisville, Kentucky")
    )
    assert result.status == Status.PASS


def test_bottler_missing_from_label_fails():
    assert check_bottler("Old Tom Distillery", read(None)).status == Status.FAIL


def test_bottled_for_counts_as_a_lead_in():
    result = check_bottler(
        "Landrevin Imports, New York, NY", read("Bottled for Landrevin Imports, New York, NY")
    )
    assert result.status == Status.PASS


@pytest.mark.parametrize(
    ("application", "label"),
    [
        # A French phrase read together with the importer statement.
        (
            "Landrevin Imports, New York, NY",
            "Mis en bouteille au château de Landrevin Imported by Landrevin Imports, New York, NY",
        ),
        # A distiller and a bottler; the application names the bottler.
        (
            "Harbor Bottling Co., Baltimore, Maryland",
            "Distilled by Old Tom Distillery, Bardstown, Kentucky "
            "Bottled by Harbor Bottling Co., Baltimore, Maryland",
        ),
        # The application names the distiller.
        (
            "Old Tom Distillery, Bardstown, Kentucky",
            "Distilled by Old Tom Distillery, Bardstown, Kentucky "
            "Bottled by Harbor Bottling Co., Baltimore, Maryland",
        ),
    ],
)
def test_one_of_several_statements_can_match(application, label):
    assert check_bottler(application, read(label)).status == Status.PASS


def test_several_statements_none_matching_still_fail():
    label = "Mis en bouteille au château Imported by Other Imports, Boston, MA"
    result = check_bottler("Landrevin Imports, New York, NY", read(label))
    assert result.status == Status.FAIL


def test_a_phrase_with_no_company_name_does_not_match():
    result = check_bottler("Landrevin Imports, New York, NY", read("Mis en bouteille au château"))
    assert result.status == Status.FAIL


# Found by review: cases where splitting into statements must not create a match.


def test_a_company_in_a_different_role_does_not_match_when_the_application_names_one():
    label = "Distilled by ABC Distillery, Bardstown, KY Bottled by XYZ Bottlers, Louisville, KY"
    result = check_bottler("Bottled by ABC Distillery, Bardstown, KY", read(label))
    assert result.status != Status.PASS


def test_the_same_role_still_matches():
    label = "Distilled by ABC Distillery, Bardstown, KY Bottled by XYZ Bottlers, Louisville, KY"
    result = check_bottler("Bottled by XYZ Bottlers, Louisville, KY", read(label))
    assert result.status == Status.PASS


def test_a_lowercase_second_statement_keeps_the_whole_address_in_the_first():
    label = (
        "Distilled by Old Tom Distillery, Louisville, Kentucky and bottled for Acme Spirits, "
        "Chicago, IL"
    )
    result = check_bottler("Old Tom Distillery, Louisville", read(label))
    assert result.status != Status.PASS


def test_by_or_for_inside_a_company_name_does_not_start_a_statement():
    # Same city and state, so it may be a trade name, but never a match.
    label = "Brewed by Hops For Heroes Brewing, Austin, TX"
    assert check_bottler("Heroes Brewing, Austin, TX", read(label)).status == Status.REVIEW


def test_a_match_on_one_statement_names_the_others():
    label = "Mis en bouteille au château Imported by Landrevin Imports, New York, NY"
    result = check_bottler("Landrevin Imports, New York, NY", read(label))
    assert result.status == Status.PASS
    assert 'The label also says "Mis en bouteille au château".' in result.reason


@pytest.mark.parametrize(
    ("text", "parts"),
    [
        (
            "Distilled and bottled by A Co, X Imported by B Co, Y",
            ["Distilled and bottled by A Co, X", "Imported by B Co, Y"],
        ),
        (
            "Grown, produced and bottled by A Co, X",
            ["Grown, produced and bottled by A Co, X"],
        ),
        (
            "Brewed and canned by Tidewick Brewing Co., Norfolk, Virginia",
            ["Brewed and canned by Tidewick Brewing Co., Norfolk, Virginia"],
        ),
        (
            "Distilled by A Co, Louisville, Kentucky and bottled for B Co, Chicago",
            ["Distilled by A Co, Louisville, Kentucky", "bottled for B Co, Chicago"],
        ),
    ],
)
def test_statements(text, parts):
    assert statements(text) == parts


# Real labels write the same company and address in many ways (found on approved labels
# in TTB's Public COLA Registry). The company, city, and state are compared.


@pytest.mark.parametrize(
    ("application", "label"),
    [
        # "LLC" left out
        ("Old Tom Distillery LLC, Bardstown, KY", "Bottled by Old Tom Distillery, Bardstown, KY"),
        # "Company" written "Co.", and the state's name for its abbreviation
        (
            "Tidewick Brewing Company, Norfolk, VA",
            "Brewed by TIDEWICK BREWING CO., NORFOLK, VIRGINIA",
        ),
        # "Inc." after a comma, and no comma between the company and the city
        ("Harbor Bottling, Inc., Baltimore, MD", "Bottled by Harbor Bottling Baltimore, Maryland"),
        # a street address and ZIP code
        (
            "Tidewick Brewing Co., Norfolk, VA",
            "Brewed by Tidewick Brewing Company 120 Water St. Norfolk, VA 23510",
        ),
        # periods in abbreviations
        ("R.J.S. Imports, Ltd., New York, NY", "Imported by RJS IMPORTS LTD. NEW YORK, N.Y."),
        # "&" for "and"
        ("Hill and Vale Winery, Napa, CA", "Produced and bottled by Hill & Vale Winery, Napa, CA"),
        # a trade name after "DBA"
        (
            "Harbor Bottling Co., Baltimore, MD",
            "Bottled by Harbor Bottling Co. DBA Bay Spirits, 12 Pier Rd, Baltimore, MD",
        ),
        # the place before "by"
        (
            "Old Tom Distillery, Bardstown, KY",
            "Distilled in Bardstown, Kentucky by Old Tom Distillery",
        ),
        # St. for Saint
        (
            "Old Tom Distillery, Saint Louis, MO",
            "Bottled by Old Tom Distillery, St. Louis, Missouri",
        ),
        # the producer abroad before the importer
        (
            "Landrevin Imports, New York, NY",
            "Produced and bottled by Domaine Exemple, Beaune, France "
            "Imported by Landrevin Imports Inc., New York, New York",
        ),
    ],
)
def test_the_same_company_and_place_written_differently_matches(application, label):
    assert check_bottler(application, read(label)).status == Status.PASS


def test_written_differently_is_noted():
    result = check_bottler(
        "Old Tom Distillery LLC, Bardstown, KY",
        read("Bottled by Old Tom Distillery, Bardstown, KY"),
    )
    assert result.note == "Matches, written differently"
    assert "Same company, city, and state" in result.reason


def test_a_different_company_in_the_same_city_may_be_a_trade_name():
    result = check_bottler(
        "Harbor Bottling Co., Baltimore, MD", read("Bottled by Bay Spirits, Baltimore, Maryland")
    )
    assert result.status == Status.REVIEW
    assert "trade name" in result.reason


def test_a_longer_company_name_is_a_different_company():
    label = read("Brewed by Tidewick Brewing Collective, Norfolk, VA")
    assert check_bottler("Tidewick Brewing, Norfolk, VA", label).status == Status.REVIEW


def test_the_same_company_in_another_city_of_the_same_state_fails():
    label = read("Bottled by Old Tom Distillery, Louisville, Kentucky")
    result = check_bottler("Old Tom Distillery, Bardstown, KY", label)
    assert result.status == Status.FAIL
    assert "different city" in result.reason


def test_the_same_company_with_no_state_on_the_label_needs_review():
    label = read("Bottled by Old Tom Distillery")
    assert check_bottler("Old Tom Distillery, Bardstown, KY", label).status == Status.REVIEW


def test_a_word_like_in_is_not_taken_for_a_state():
    # "IN" is Indiana, but not in "Distilled in Bardstown".
    label = read("Distilled in Bardstown by Old Tom Distillery")
    assert check_bottler("Old Tom Distillery, Lafayette, IN", label).status == Status.REVIEW


def test_another_company_in_another_place_still_fails():
    label = read("Bottled by Ridgewick Spirits LLC, Lexington, KY")
    assert check_bottler("Old Tom Distillery, Bardstown, KY", label).status == Status.FAIL


def test_a_match_in_another_role_needs_review_and_says_which():
    label = "Distilled by ABC Distillery, Bardstown, KY Bottled by XYZ Bottlers, Louisville, KY"
    result = check_bottler("Bottled by ABC Distillery, Bardstown, KY", read(label))
    assert result.status == Status.REVIEW
    assert '"Distilled by"' in result.reason and '"Bottled by"' in result.reason


# Labels print other words with the class or type (found on approved labels in TTB's
# Public COLA Registry): an appellation, a fanciful name, "Premium".


@pytest.mark.parametrize(
    ("application", "label"),
    [
        ("Vodka", "Premium Vodka"),
        ("Straight Bourbon Whiskey", "Wheated Straight Bourbon Whiskey"),
        ("Cabernet Sauvignon", "Napa Valley Cabernet Sauvignon"),
        ("India Pale Ale", "Hillside India Pale Ale"),
        ("Tequila", "Tequila 100% Agave"),
    ],
)
def test_a_class_with_other_words_matches_with_a_note(application, label):
    result = check_class(application, read(label))
    assert result.status == Status.PASS
    assert result.note == "Matches, with other words"


@pytest.mark.parametrize(
    ("application", "label", "added"),
    [
        ("Vodka", "Raspberry Flavored Vodka", "flavored"),
        ("Bourbon Whiskey", "Straight Bourbon Whiskey", "straight"),
        ("Red Wine", "Sparkling Red Wine", "sparkling"),
        ("Lager", "Non-Alcoholic Lager", "alcoholic"),
        ("Whisky", "Light Whisky", "light"),
    ],
)
def test_words_that_make_another_class_need_review(application, label, added):
    result = check_class(application, read(label))
    assert result.status == Status.REVIEW
    assert f'adds "{added}"' in result.reason


@pytest.mark.parametrize(
    ("application", "label"),
    [
        ("India Pale Ale", "Pale Ale"),  # the label leaves words out
        ("Rum", "Rumble Ale"),  # whole words only
        ("Gin", "Ginger Beer"),
        ("Bourbon Whiskey", "Whiskey Bourbon"),  # in another order
    ],
)
def test_a_class_not_on_the_label_as_a_whole_phrase_fails(application, label):
    assert check_class(application, read(label)).status == Status.FAIL


def test_the_class_rules_still_apply_first():
    assert check_class("Vodka", read("VODKA")).note == "Matches, different capitals"
    assert check_class("Vodka", read(None)).status == Status.FAIL


# The brand. Labels often show a fanciful name more prominently than the brand, or print
# the brand only in the bottler statement (found on approved labels in TTB's Public COLA
# Registry), so the AI reader can take another name for the brand.


def label_reading(brand, bottler=None, class_type="Cabernet Sauvignon"):
    return LabelReading(
        brand_name=read(brand),
        class_type=read(class_type),
        alcohol_content=read("13.5% Alc./Vol."),
        net_contents=read("750 mL"),
        bottler_name_address=read(bottler, image_number=2),
        country_of_origin=read(None),
        government_warning=read_warning(GOVERNMENT_WARNING),
        image_problems=[],
    )


def tesseract(*pages):
    """Tesseract's words, one pass for each picture."""
    return [[[Word(word, 0, 0, 10, 10) for word in page.split()]] for page in pages]


def test_a_brand_found_in_the_bottler_statement_matches_and_says_where():
    reading = label_reading("Midnight Owl", "Produced and bottled by Harbor Hill Cellars, Napa, CA")
    result = check_brand("HARBOR HILL CELLARS", reading)
    assert result.status == Status.PASS
    assert result.note == "Matches, found in the bottler statement"
    assert 'took "Midnight Owl" for the brand name' in result.reason
    assert "on image 2" in result.reason


def test_a_brand_read_with_other_words_matches():
    result = check_brand("HARBOR HILL", label_reading("Harbor Hill Midnight Owl"))
    assert (result.status, result.note) == (Status.PASS, "Matches, with other words")


def test_a_brand_found_by_basic_text_reading_says_which_image():
    ocr = tesseract("Midnight Owl Cabernet", "HARBOR HILL CELLARS est. 1998")
    result = check_brand("Harbor Hill Cellars", label_reading("Midnight Owl"), ocr)
    assert (result.status, result.note) == (Status.PASS, "Matches, found on image 2")
    assert "found by basic text reading" in result.reason


def test_only_the_whole_brand_counts():
    ocr = tesseract("Midnight Owl by Harbor Hill")
    reading = label_reading("Midnight Owl", "Bottled by Harbor Hill, Napa, CA")
    assert check_brand("Harbor Hill Cellars", reading, ocr).status == Status.FAIL


def test_a_short_brand_is_not_looked_for_elsewhere():
    reading = label_reading("Midnight Owl", "Bottled by Oak Cellars, Napa, CA")
    assert check_brand("OAK", reading, tesseract("OAK BARREL AGED")).status == Status.FAIL


def test_the_warning_and_the_class_dont_count_as_the_brand():
    assert (
        check_brand(
            "Surgeon General", label_reading("Midnight Owl"), tesseract(GOVERNMENT_WARNING)
        ).status
        == Status.FAIL
    )
    reading = label_reading("Midnight Owl", class_type="Straight Bourbon Whiskey")
    ocr = tesseract("Straight Bourbon Whiskey")
    assert check_brand("Straight Bourbon", reading, ocr).status == Status.FAIL


def test_a_planted_brand_still_fails():
    reading = label_reading("Midnight Owl", "Produced and bottled by Harbor Hill Cellars, Napa, CA")
    ocr = tesseract("Midnight Owl", "Harbor Hill Cellars")
    assert check_brand("HARBOR VALE CELLARS", reading, ocr).status == Status.FAIL


def test_a_brand_the_ai_reader_missed_can_be_found_elsewhere():
    reading = label_reading(None, "Produced and bottled by Harbor Hill Cellars, Napa, CA")
    result = check_brand("Harbor Hill Cellars", reading)
    assert result.status == Status.PASS
    assert result.reason.startswith('The application\'s brand name, "Harbor Hill Cellars", is on')
