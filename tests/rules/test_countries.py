import pytest

from app.rules.countries import COUNTRY_NAMES, PARENTS, find_countries, match_key
from app.rules.countries import check_country as check
from app.rules.results import Status
from tests.rules.helpers import read


@pytest.mark.parametrize(
    ("text", "country"),
    [
        ("Product of France", "France"),
        ("PRODUCT OF FRANCE", "France"),
        ("Produkt aus Deutschland", "Germany"),
        ("Hecho en México", "Mexico"),
        ("Product of U.S.A.", "United States"),
        ("日本産", "Japan"),
        ("Product of Northern Ireland", "Northern Ireland"),
        ("Product of Scotland, United Kingdom", "Scotland"),
        ("Product of Trinidad & Tobago", "Trinidad and Tobago"),
    ],
)
def test_find_countries(text, country):
    assert [found for found, _ in find_countries(text)] == [country]


def test_a_country_name_inside_a_word_does_not_count():
    assert find_countries("Product of Usability Labs") == []


def test_no_name_belongs_to_two_countries():
    owners = {}
    for country, others in COUNTRY_NAMES.items():
        for name in [country, *others]:
            assert owners.setdefault(match_key(name), country) == country, name


def test_every_parent_is_in_the_table():
    for place, country in PARENTS.items():
        assert place in COUNTRY_NAMES and country in COUNTRY_NAMES


@pytest.mark.parametrize(
    ("application", "label", "status", "note"),
    [
        ("France", "Product of France", Status.PASS, None),
        ("Mexico", "Hecho en México", Status.PASS, None),
        ("USA", "Product of U.S.A.", Status.PASS, None),
        ("Germany", "Produkt aus Deutschland", Status.PASS, "Matches, Deutschland = Germany"),
        ("Japan", "日本産", Status.PASS, "Matches, 日本 = Japan"),
        (
            "United Kingdom",
            "Product of Scotland",
            Status.PASS,
            "Matches, Scotland is part of the United Kingdom",
        ),
        ("Scotland", "Product of Scotland, United Kingdom", Status.PASS, None),
        ("France", "Product of Italy", Status.FAIL, None),
        ("Ireland", "Product of Northern Ireland", Status.FAIL, None),
        ("Scotland", "Product of England", Status.FAIL, None),
    ],
)
def test_country_matching(application, label, status, note):
    result = check(application, read(label))
    assert result.status == status
    assert result.note == note


def test_domestic_product_needs_no_country():
    assert check("", read(None)).status == Status.NOT_NEEDED
    assert check("", read("Product of USA")).status == Status.NOT_NEEDED
    assert check("", read("Product of Puerto Rico")).status == Status.NOT_NEEDED


def test_import_missing_its_country_fails():
    result = check("France", read(None))
    assert result.status == Status.FAIL
    assert "imports must show it" in result.reason


@pytest.mark.parametrize(
    ("application", "label"),
    [
        ("", read("Product of France")),  # label names a country the application doesn't
        ("France", read("Product of Freedonia")),  # not in the table
        ("France", read("Product of France and Italy")),  # two countries
        ("France", read("Product of France", readability="unclear")),
        ("France", read("Product of Fr[?]nce")),
        ("Atlantis", read("Product of France")),  # application country not in the table
        # Found only through the AI's translation, so a person should look.
        ("Japan", read("ニッポン", english_meaning="Japan")),
    ],
)
def test_needs_review(application, label):
    assert check(application, label).status == Status.REVIEW


def test_domestic_application_needs_no_country_on_the_label():
    for said in ("USA", "United States", "Puerto Rico"):
        assert check(said, read(None)).status == Status.NOT_NEEDED


# A country named only in the bottler or importer statement (found on approved labels in
# TTB's Public COLA Registry, third set).


@pytest.mark.parametrize(
    ("application", "bottler"),
    [
        ("SCOTLAND", "Distilled & bottled in Scotland by Old Tom Distillers, Glasgow"),
        (
            "FRANCE",
            "Brewed by Brasserie Exemple, Lille, France Imported by Landrevin Imports, Boston, MA",
        ),
        ("UNITED KINGDOM", "Distilled & bottled in Scotland by Old Tom Distillers, Glasgow"),
    ],
)
def test_a_country_only_in_the_bottler_statement_needs_review(application, bottler):
    result = check(application, read(None), read(bottler))
    assert result.status == Status.REVIEW
    assert "only in the bottler or importer statement" in result.reason


def test_another_country_in_the_bottler_statement_still_fails():
    bottler = read("Distilled & bottled in Scotland by Old Tom Distillers, Glasgow")
    assert check("IRELAND", read(None), bottler).status == Status.FAIL


def test_no_country_anywhere_still_fails():
    bottler = read("Imported by Landrevin Imports, Boston, MA")
    assert check("FRANCE", read(None), bottler).status == Status.FAIL
    assert check("FRANCE", read(None)).status == Status.FAIL


def test_a_country_statement_is_compared_as_before():
    bottler = read("Bottled in Scotland by Old Tom Distillers, Glasgow")
    assert check("FRANCE", read("Product of France"), bottler).status == Status.PASS
    assert check("", read(None), bottler).status == Status.NOT_NEEDED
