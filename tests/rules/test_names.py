import pytest

from app.rules.names import check_bottler, check_name, statements
from app.rules.results import Status
from tests.rules.helpers import read


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
            Status.REVIEW,
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
    label = "Brewed by Hops For Heroes Brewing, Austin, TX"
    assert check_bottler("Heroes Brewing, Austin, TX", read(label)).status == Status.FAIL


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
