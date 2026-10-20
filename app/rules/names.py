"""Matching rules for names: brand name, class/type, and bottler name and address."""

import re
from dataclasses import dataclass, replace

from app.reading.schema import FieldReading, LabelReading
from app.reading.words import Passes
from app.rules.places import US_STATES
from app.rules.results import Check, Status
from app.rules.text import (
    cosmetic_differences,
    is_missing,
    is_unclear,
    join_words,
    loose_key,
    non_latin_script,
    tidy,
    without_accents,
    without_punctuation,
)

# Words such as "Bottled by", "Distilled and bottled by", "Imported by", or
# "Bottled for" at the start.
LEAD_IN = re.compile(r"^\s*(?:[^\W\d_]+[\s,&]+){1,6}?(?:by|for)\b\s*:?\s*", re.IGNORECASE)


def check_name(what: str, application: str, label: FieldReading) -> Check:
    """Compare a name on the label with the application.

    `what` names the field in messages, for example "brand name".
    """
    if is_missing(label):
        return Check(Status.FAIL, f"The label doesn't show the {what}.")
    said, shown = tidy(application), tidy(label.text or "")
    if not said:
        return Check(
            Status.REVIEW, f'The application leaves the {what} blank. The label says "{shown}".'
        )
    if is_unclear(label):
        return Check(
            Status.REVIEW,
            f"Part of the {what} is hard to read on the label. Please check it by eye.",
        )
    return compare_names(what, said, shown)


def compare_names(what: str, said: str, shown: str) -> Check:
    both = f'The label says "{shown}" and the application says "{said}".'
    if said == shown:
        return Check(Status.PASS, f"The {what} matches the application.")
    if loose_key(said) == loose_key(shown):
        differences = join_words(cosmetic_differences(said, shown))
        return Check(
            Status.PASS,
            f"{both} Only the {differences} differ.",
            note=f"Matches, different {differences}",
        )
    if loose_key(without_accents(said)) == loose_key(without_accents(shown)):
        return Check(Status.REVIEW, f"{both} The accents differ. Please check.")
    label_script = non_latin_script(shown)
    if label_script and not non_latin_script(said):
        return Check(
            Status.REVIEW,
            f'The label shows the {what} in {label_script} script ("{shown}") and the '
            f'application uses a romanized spelling ("{said}"). Please check by eye.',
        )
    return Check(Status.FAIL, f'The label says "{shown}" but the application says "{said}".')


# Words that make a different class or type when added to one, from TTB's standards of
# identity (checked in the eCFR, Title 27 up to date as of Oct 16, 2026): 4.21 for wine
# ("sparkling", "dessert", "table", "fruit", ...), 5.142, 5.143, and 5.150 for spirits
# ("flavored vodka", "straight", "blended", "light", "spirit" whisky, cordials and
# liqueurs), and 7.65 for malt beverages ("low alcohol", "non-alcoholic", "alcohol free").
CLASS_CHANGING = {
    "straight", "blended", "light", "spirit", "flavored", "flavoured", "cordial", "liqueur",
    "sparkling", "carbonated", "crackling", "petillant", "pétillant", "frizzante", "dessert",
    "table", "aperitif", "imitation", "substandard", "citrus", "fruit", "berry", "retsina",
    "sake", "alcohol", "alcoholic", "nonalcoholic",
}  # fmt: skip


def name_words(text: str) -> list[str]:
    return without_punctuation(tidy(text)).casefold().split()


def find_words(wanted: list[str], words: list[str]) -> int | None:
    """Where the wanted words start among the words, as a whole phrase, or None."""
    size = len(wanted)
    for i in range(len(words) - size + 1):
        if words[i : i + size] == wanted:
            return i
    return None


def check_class(application: str, label: FieldReading) -> Check:
    """Labels often print other words with the class or type: an appellation, a fanciful
    name, "Premium". If the application's whole class or type is among them, it matches,
    unless the other words can make it a different class, as in "Flavored Vodka"."""
    what = "class or type"
    result = check_name(what, application, label)
    if result.status != Status.FAIL or is_missing(label):
        return result
    said, shown = tidy(application), tidy(label.text or "")
    wanted, words = name_words(said), name_words(shown)
    start = find_words(wanted, words) if wanted else None
    if start is None:
        return result
    added = words[:start] + words[start + len(wanted) :]
    changing = [word for word in added if word in CLASS_CHANGING]
    if changing:
        return Check(
            Status.REVIEW,
            f'The label\'s class or type, "{shown}", includes the application\'s "{said}", but '
            f'adds "{" ".join(changing)}", which can make it a different class or type. '
            "Please check.",
        )
    return Check(
        Status.PASS,
        f'The label says "{shown}", which includes the application\'s "{said}" with other words.',
        note="Matches, with other words",
    )


# The application's brand is looked for elsewhere on the label only if it has at least
# this many letters and digits, so a short common word can't match by accident.
SEARCHED_BRAND = 6
WARNING_WORDS = 45  # about as many as the government warning has


def without_warning(words: list[str]) -> list[str]:
    """A page's words without the government warning, from its heading to "problems"."""
    for i in range(len(words) - 1):
        if words[i] == "government" and words[i + 1].startswith("warning"):
            end = next(
                (
                    j
                    for j in range(i, min(len(words), i + WARNING_WORDS + 10))
                    if words[j] == "problems"
                ),
                i + WARNING_WORDS,
            )
            return words[:i] + words[end + 1 :]
    return words


def written_differently(wanted: list[str], words: list[str]) -> bool:
    """Whether the words hold the wanted ones with other spacing or company form: "QuillMere
    Brewing Company" for "Quill Mere Brewing Co.". Whole words only, so "Air" is never found
    in "Chair"."""
    target = "".join(w for w in wanted if w not in LEGAL_FORMS)
    kept = [w for w in words if w not in LEGAL_FORMS]
    for i in range(len(kept)):
        joined = ""
        for word in kept[i:]:
            joined += word
            if joined == target:
                return True
            if len(joined) >= len(target):
                break
    return False


def check_brand(application: str, reading: LabelReading, ocr: Passes | None = None) -> Check:
    """The brand on the label, as the AI reader took it, against the application. Labels
    often show a fanciful name more prominently than the brand, or print the brand only
    in the bottler statement. So if they differ, the application's whole brand is looked
    for elsewhere on the label, and the note says where it was found. It matches only when
    found as written and at least SEARCHED_BRAND letters long. A shorter brand, which a
    common word could match by accident, or one written differently, needs review."""
    what = "brand name"
    label = reading.brand_name
    result = check_name(what, application, label)
    if result.status != Status.FAIL:
        return result
    said = tidy(application)
    wanted = name_words(said)
    if not wanted:
        return result
    short = len("".join(wanted)) < SEARCHED_BRAND
    shown = tidy(label.text or "")
    # The words of a class or type, such as "Straight Bourbon", aren't a brand.
    class_words = name_words(reading.class_type.text or "")
    if find_words(wanted, class_words) is not None or written_differently(wanted, class_words):
        return result

    bottler = reading.bottler_name_address
    places = []  # (where, the words there, the note if it matches)
    if not is_missing(label):
        places.append(("in the brand name it read", name_words(shown), "Matches, with other words"))
    if bottler.text:
        places.append(
            (
                f'in the bottler statement on image {bottler.image_number}: "{tidy(bottler.text)}"',
                name_words(bottler.text),
                "Matches, found in the bottler statement",
            )
        )
    for number, passes in enumerate(ocr or [], start=1):
        for words in passes:
            page = without_warning(name_words(" ".join(word.text for word in words)))
            places.append(
                (
                    f"on image {number}, found by basic text reading",
                    page,
                    f"Matches, found on image {number}",
                )
            )

    took = (
        f'The AI reader took "{shown}" for the brand name, but the application\'s "{said}" is '
        "also on the label"
        if not is_missing(label)
        else f'The application\'s brand name, "{said}", is on the label'
    )
    for where, words, note in places:
        if find_words(wanted, words) is None:
            continue
        if short:
            return Check(
                Status.REVIEW,
                f"{took}, {where}. It is short, so it could be another word. Please check it "
                "is the brand.",
            )
        if where == "in the brand name it read":
            return Check(
                Status.PASS,
                f'The label\'s brand name, "{shown}", includes the application\'s "{said}" with '
                "other words.",
                note=note,
            )
        return Check(Status.PASS, f"{took}, {where}.", note=note)
    for where, words, _ in places:
        if written_differently(wanted, words):
            return Check(
                Status.REVIEW,
                f"{took} written differently, {where}. Please check it is the same brand.",
            )
    return result


def strip_lead_in(text: str) -> str:
    return LEAD_IN.sub("", tidy(text), count=1)


# Words that say what a company did, before "by" or "for": "Distilled and bottled by",
# "Imported by", "Bottled for". Only these start a new statement in a bottler field.
ACTIONS = {
    "aged", "blended", "bottled", "brewed", "canned", "cellared", "crafted", "distilled",
    "distributed", "estate", "fermented", "finished", "grown", "imported", "kegged", "made",
    "manufactured", "packaged", "packed", "prepared", "produced", "rectified", "vinted",
}  # fmt: skip
JOINERS = {"and", "&"}


def bare(word: str) -> str:
    return "".join(c for c in word.casefold() if c.isalnum() or c == "&")


def statements(text: str) -> list[str]:
    """A bottler field split into its statements. Labels often carry more than one,
    such as "Distilled by ..." and "Bottled by ...", or a French "Mis en bouteille au
    château" next to "Imported by ...". A statement starts at the words saying what a
    company did, just before "by" or "for", so "by" or "for" inside a company name
    never starts one."""
    words = tidy(text).split()
    starts = {0}
    for i, word in enumerate(words):
        if bare(word) not in ("by", "for"):
            continue
        start, j = i, i - 1
        while j >= 0:
            if bare(words[j]) in ACTIONS:
                start = j
            elif not (bare(words[j]) in JOINERS and j > 0 and bare(words[j - 1]) in ACTIONS):
                break
            j -= 1
        if start < i:
            starts.add(start)
    bounds = sorted(starts) + [len(words)]
    parts = []
    for a, b in zip(bounds, bounds[1:], strict=False):
        part = words[a:b]
        while part and bare(part[-1]) in JOINERS:
            part = part[:-1]  # "..., Kentucky and" before "bottled for ..."
        if part:
            parts.append(" ".join(part))
    return parts


def lead_in(statement: str) -> str:
    """The words before the company, such as "Distilled by"."""
    match = LEAD_IN.match(tidy(statement))
    return match.group(0).strip(" :") if match else ""


def role(statement: str) -> set[str]:
    """What the company did, from the words before "by" or "for": {"bottled"} for
    "Bottled by ...". Empty if the statement doesn't say."""
    match = LEAD_IN.match(tidy(statement))
    return {bare(word) for word in match.group(0).split()} & ACTIONS if match else set()


# Words that only give a company's legal form. Labels often leave them out.
LEGAL_FORMS = {
    "co", "company", "corp", "corporation", "inc", "incorporated", "llc", "lllp", "llp", "lp",
    "ltd", "limited", "pllc", "plc", "gmbh", "srl", "sarl",
}  # fmt: skip
# Short forms in place names: St. Louis is Saint Louis.
PLACE_WORDS = {"saint": "st", "mount": "mt", "fort": "ft"}
SEPARATOR = ","
ZIP = re.compile(r"^\d{5}(?:\d{4})?$")
STREET = re.compile(r"^\d+[A-Za-z]?(?:-\d+)?\s+\S")  # "120 Kestrel St", "12B Kestrel St"


def address_words(text: str) -> list[str]:
    """The lower-case words of a name and address. "&" is "and", periods and apostrophes
    are dropped (N.Y. is ny), and other punctuation becomes a separator."""
    text = tidy(text).casefold().replace("&", " and ").replace(".", "").replace("'", "")
    return [
        PLACE_WORDS.get(word, word) if word[0].isalnum() else SEPARATOR
        for word in re.findall(r"[^\W_]+|[^\w\s]", text)
    ]


def words_only(words: list[str]) -> list[str]:
    return [word for word in words if word != SEPARATOR]


def state_code(words: list[str]) -> str | None:
    """The postal abbreviation, if the words are a state's name or abbreviation."""
    joined = " ".join(words)
    for code, name in US_STATES.items():
        if joined in (code.casefold(), name.casefold()):
            return code
    return None


@dataclass(frozen=True)
class Address:
    company: list[str]  # its words, without legal forms such as LLC
    city: list[str]
    state: str  # postal abbreviation


def parse_address(text: str) -> Address | None:
    """A name and address written "Company, City, State", as in an application, or None
    if it isn't in that form. A street between the company and the city is ignored."""
    parts = [part.strip() for part in tidy(text).split(",") if part.strip()]
    if len(parts) < 3:
        return None
    state = state_code(words_only(address_words(re.sub(r"\s*[\d-]{5,10}$", "", parts[-1]))))
    if state is None:
        return None
    # The first part is the company, even with a digit in its name ("3 Rivers Brewing"). A later
    # part starting with a street number is a street address, and is ignored.
    company = [
        word
        for number, part in enumerate(parts[:-2])
        if number == 0 or not STREET.match(part)
        for word in words_only(address_words(part))
        if word not in LEGAL_FORMS
    ]
    city = words_only(address_words(parts[-2]))
    if not company or not city:
        return None
    return Address(company, city, state)


def starts_with_company(address: Address, words: list[str]) -> bool:
    """Whether the words begin with the company's whole name. Legal forms and punctuation
    may differ. The name must end there: "Tidewick Brewing" is not "Tidewick Brewing
    Collective", but it may be followed by a street, "DBA", or the city."""
    i = 0

    def skip(i: int) -> int:
        while i < len(words) and (words[i] == SEPARATOR or words[i] in LEGAL_FORMS):
            i += 1
        return i

    for word in address.company:
        i = skip(i)
        if i >= len(words) or words[i] != word:
            return False
        i += 1
    if skip(i) > i or i == len(words):
        return True
    following = words[i]
    return (
        following == "dba"
        or any(c.isdigit() for c in following)
        or words_only(words[i:])[: len(address.city)] == address.city
    )


def state_names(state: str) -> list[list[str]]:
    return [[state.casefold()], US_STATES[state].casefold().split()]


def has_place(address: Address, words: list[str]) -> bool:
    """Whether the words give the city followed by its state, by name or abbreviation."""
    plain = words_only(words)
    size = len(address.city)
    for i in range(len(plain) - size + 1):
        if plain[i : i + size] == address.city:
            rest = plain[i + size :]
            if any(rest[: len(name)] == name for name in state_names(address.state)):
                return True
    return False


def has_state(state: str, words: list[str]) -> bool:
    """Whether the words name the state: in full, or as its abbreviation after a comma or
    before a ZIP code or the end. So the word "in" isn't taken for Indiana."""
    full, short = state_names(state)[1], state.casefold()
    plain = words_only(words)
    if any(plain[i : i + len(full)] == full for i in range(len(plain))):
        return True
    for i, word in enumerate(words):
        if word != short:
            continue
        after = words[i + 1] if i + 1 < len(words) else None
        if (
            (i > 0 and words[i - 1] == SEPARATOR)
            or after in (None, SEPARATOR)
            or (after and ZIP.match(after))
        ):
            return True
    return False


def same_name_or(result: Check, said: str, shown: str) -> Check:
    """For a name and address not written "Company, City, State": the same company
    name before the first comma needs review."""
    said_name, shown_name = said.split(",")[0], shown.split(",")[0]
    if loose_key(said_name) == loose_key(shown_name):
        return Check(
            Status.REVIEW,
            f'Same company name, but the address is written differently. The label says "{shown}" '
            f'and the application says "{said}".',
        )
    return result


def compare_bottler(what: str, application: str, statement: str) -> Check:
    """One statement on the label against the application. The company, city, and state
    are compared, not the exact words: labels leave out "LLC", spell the state out, or
    add a street address and ZIP code."""
    said, shown = strip_lead_in(application), strip_lead_in(statement)
    result = compare_names(what, said, shown)
    if result.status != Status.FAIL:
        return result
    address = parse_address(said)
    if address is None:
        return same_name_or(result, said, shown)
    company = starts_with_company(address, address_words(shown))
    # The place can be in the words before "by": "Bottled in Napa, California by ...".
    place = has_place(address, address_words(statement))
    both = f'The label says "{shown}" and the application says "{said}".'
    if company and place:
        return Check(
            Status.PASS,
            f"{both} Same company, city, and state, written differently.",
            note="Matches, written differently",
        )
    if company and has_state(address.state, address_words(statement)):
        return Check(
            Status.FAIL,
            f'Same company name, but a different city. The label says "{shown}" but the '
            f'application says "{said}".',
        )
    if company:
        return Check(
            Status.REVIEW,
            f"Same company name, but the address is written differently. {both}",
        )
    if place:
        return Check(
            Status.REVIEW,
            f'The label names a different company in the same city and state: "{shown}". The '
            f'application says "{said}". It may be a trade name the company uses. Please check.',
        )
    return result


RANK = {Status.PASS: 0, Status.REVIEW: 1, Status.FAIL: 2}


def check_bottler(application: str, label: FieldReading) -> Check:
    """Compare the bottler or importer name and address, ignoring words like "Bottled by"."""
    what = "bottler name and address"
    if is_missing(label):
        return Check(Status.FAIL, f"The label doesn't show the {what}.")
    said, shown = strip_lead_in(application), strip_lead_in(label.text or "")
    if not said:
        return Check(
            Status.REVIEW, f'The application leaves the {what} blank. The label says "{shown}".'
        )
    if is_unclear(label):
        return Check(
            Status.REVIEW,
            f"Part of the {what} is hard to read on the label. Please check it by eye.",
        )
    # The label may name several companies, such as a distiller and a bottler, or a
    # producer and an importer. One of them can match, but only in the role the
    # application gives it, if it gives one.
    parts = statements(label.text or "")
    if len(parts) <= 1:
        return compare_bottler(what, application, label.text or "")
    wanted = role(application)
    results = []
    for part in parts:
        result = compare_bottler(what, application, part)
        if result.status == Status.PASS and not wanted <= role(part):
            result = Check(
                Status.REVIEW,
                f'The label names this company, but after "{lead_in(part)}", where the '
                f'application says "{lead_in(application)}". Please check.',
            )
        results.append((part, result))
    part, best = min(results, key=lambda pair: RANK[pair[1].status])
    if best.status == Status.PASS:
        others = "; ".join(p for p in parts if p is not part)
        return replace(best, reason=f'{best.reason} The label also says "{others}".')
    if best.status == Status.REVIEW:
        return best
    return same_name_or(compare_names(what, said, shown), said, shown)
