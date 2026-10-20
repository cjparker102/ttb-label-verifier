"""The app's rules must be general: based on the regulations and common label patterns,
never on the labels they were tested on. So no brand, company, or place name from a
private set of real labels (in private/, never committed) may appear in the app's code.

The names come from each set's application data, its registry records, and what was read
from its labels. A word or phrase that was already in the app before the first real-label
set was fetched doesn't count, nor do the generic words below: those were not taken from
the labels. Without a private set, as in CI, there is nothing to check against."""

import json
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PRIVATE = ROOT / "private"
APP = "app"
# The last commit before the first real-label set was fetched (Oct 20, 2026).
BEFORE_REAL_LABELS = "d4d5954"
CODE = re.compile(r"\.(py|html|js|css|txt|json)$")
LONGEST = 4  # words in the longest phrase checked

# Words that occur in company names, addresses, and class names in general.
GENERIC = {
    # company forms and trade words
    "and", "the", "of", "co", "company", "corp", "corporation", "inc", "incorporated",
    "llc", "ltd", "limited", "lp", "llp", "plc", "dba", "srl", "sa", "spa", "gmbh",
    "group", "imports", "importers", "importing", "import", "beverage", "beverages",
    "spirits", "wine", "wines", "winery", "vineyard", "vineyards", "cellars", "cellar",
    "brewing", "brewery", "brewers", "brew", "distillery", "distillers", "distilling",
    "estate", "estates", "farm", "farms", "family", "collective", "society",
    # address words
    "street", "st", "avenue", "ave", "road", "rd", "drive", "dr", "lane", "ln", "route",
    "suite", "ste", "highway", "hwy", "north", "south", "east", "west", "nw", "ne", "sw", "se",
    "city", "new", "san", "santa", "saint", "fort", "port", "lake", "lakes", "valley",
    # label words
    "bottled", "produced", "made", "brewed", "distilled", "imported", "packaged", "by", "for",
    "in", "at", "product", "premium", "reserve", "beer", "ale", "lager", "stout",
    "porter", "pale", "india", "red", "white", "blend", "rose", "sparkling", "whiskey",
    "whisky", "bourbon", "rye", "straight", "vodka", "gin", "rum", "tequila", "agave",
}  # fmt: skip


def words(text: str) -> list[str]:
    """Lower-case words of letters only; numbers such as streets and ZIP codes are dropped."""
    text = text.casefold().replace("&", " and ").replace("'", "").replace("’", "")
    return [w for w in re.split(r"[^\w]+", text) if w.isalpha() and len(w) >= 3]


def phrases(text: str) -> set[tuple[str, ...]]:
    found = set()
    for part in re.split(r"[,|•/:;()]", text):
        part_words = words(part)
        for size in range(1, LONGEST + 1):
            for i in range(len(part_words) - size + 1):
                found.add(tuple(part_words[i : i + size]))
    return found


def names_in_private_sets() -> set[tuple[str, ...]]:
    texts = []
    for path in PRIVATE.glob("**/cases.json"):
        for case in json.loads(path.read_text(encoding="utf-8")):
            texts += [
                case["application"]["brand_name"],
                case["application"]["bottler_name_address"],
            ]
    for path in PRIVATE.glob("**/labels/*/record.json"):
        record = json.loads(path.read_text(encoding="utf-8"))
        keys = ("brand", "fanciful", "applicant", "wine_appellation")
        texts += [record.get(key) or "" for key in keys]
    for path in PRIVATE.glob("**/results-*.json"):
        for result in json.loads(path.read_text(encoding="utf-8"))["records"]:
            for field in ("brand_name", "class_type", "bottler_name_address"):
                texts.append(((result.get("reading") or {}).get(field) or {}).get("text") or "")
    found = set().union(*(phrases(text) for text in texts)) if texts else set()
    return {p for p in found if not set(p) <= GENERIC and not states_or_countries(p)}


def states_or_countries(phrase: tuple[str, ...]) -> bool:
    """US states and countries are in the app's general tables, not taken from labels."""
    from app.rules.countries import COUNTRY_NAMES
    from app.rules.places import US_STATES

    places = {
        tuple(words(name))
        for country, others in COUNTRY_NAMES.items()
        for name in [country, *others]
    } | {tuple(words(name)) for name in US_STATES.values()}
    return phrase in places or set(phrase) <= GENERIC | {w for p in places for w in p}


def code_phrases(files: dict[str, str]) -> set[tuple[str, ...]]:
    return set().union(*(phrases(text) for text in files.values()))


def app_now() -> dict[str, str]:
    return {
        str(p): p.read_text(encoding="utf-8")
        for p in (ROOT / APP).rglob("*")
        if p.is_file() and CODE.search(p.name)
    }


def app_before() -> dict[str, str]:
    def git(*args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout

    names = git("ls-tree", "-r", "--name-only", BEFORE_REAL_LABELS, APP).split()
    return {
        name: git("show", f"{BEFORE_REAL_LABELS}:{name}") for name in names if CODE.search(name)
    }


def test_no_name_from_a_real_label_set_is_in_the_app():
    names = names_in_private_sets()
    if not names:
        pytest.skip("no private set of real labels here")
    new = (names & code_phrases(app_now())) - code_phrases(app_before())
    assert not new, f"Names from the test set in the app's code: {sorted(new)}"


def test_the_check_finds_a_name_added_to_the_code():
    """The check itself works: a phrase from a name, new to the code, is caught."""
    names = {("stonebridge", "hollow")}
    before = code_phrases({"a.py": "def check(): pass"})
    after = code_phrases({"a.py": 'TRADE_NAMES = ["Stonebridge Hollow"]\ndef check(): pass'})
    assert (names & after) - before == {("stonebridge", "hollow")}
    assert not (names & before)
