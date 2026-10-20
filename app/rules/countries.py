"""Matching rules for the country of origin.

Country names in any language map to one standard English name, using the table
below. It covers countries that commonly export alcohol to the US, with their
names in their own languages and in the main European languages.
"""

import re
import unicodedata

from app.reading.schema import FieldReading
from app.rules.results import Check, Status
from app.rules.text import is_missing, is_unclear, non_latin_script, tidy

COUNTRY_NAMES: dict[str, list[str]] = {
    "United States": [
        "USA",
        "U.S.A.",
        "U.S.",
        "US",
        "United States of America",
        "Estados Unidos",
        "États-Unis",
        "Stati Uniti",
        "Vereinigte Staaten",
    ],
    "Puerto Rico": [],
    "U.S. Virgin Islands": ["US Virgin Islands"],
    "Canada": ["Canadá", "Kanada"],
    "Mexico": ["México", "Mexique", "Messico", "Mexiko"],
    "France": ["Francia", "Frankreich", "Frankrijk"],
    "Italy": ["Italia", "Italie", "Italien"],
    "Spain": ["España", "Espagne", "Spagna", "Spanien"],
    "Portugal": ["Portogallo"],
    "Germany": ["Deutschland", "Allemagne", "Alemania", "Germania", "Duitsland"],
    "Austria": ["Österreich", "Autriche"],
    "Switzerland": ["Schweiz", "Suisse", "Svizzera", "Suiza", "Helvetia"],
    "United Kingdom": [
        "UK",
        "U.K.",
        "Great Britain",
        "Britain",
        "Royaume-Uni",
        "Reino Unido",
        "Regno Unito",
        "Vereinigtes Königreich",
    ],
    "Scotland": ["Écosse", "Escocia", "Scozia", "Schottland"],
    "England": ["Angleterre", "Inglaterra", "Inghilterra"],
    "Wales": ["Cymru", "Pays de Galles", "Gales", "Galles"],
    "Northern Ireland": ["Irlande du Nord", "Irlanda del Norte", "Nordirland"],
    "Ireland": ["Éire", "Irlande", "Irlanda", "Irland", "Republic of Ireland"],
    "Netherlands": [
        "The Netherlands",
        "Nederland",
        "Holland",
        "Pays-Bas",
        "Países Bajos",
        "Paesi Bassi",
        "Niederlande",
    ],
    "Belgium": ["België", "Belgique", "Belgien", "Bélgica", "Belgio"],
    "Denmark": ["Danmark", "Danemark", "Dinamarca", "Dänemark", "Danimarca"],
    "Sweden": ["Sverige", "Suède", "Suecia", "Schweden", "Svezia"],
    "Norway": ["Norge", "Noreg", "Norvège", "Noruega", "Norwegen", "Norvegia"],
    "Finland": ["Suomi", "Finlande", "Finlandia", "Finnland"],
    "Iceland": ["Ísland", "Islande", "Islandia"],
    "Poland": ["Polska", "Pologne", "Polonia", "Polen"],
    "Czech Republic": [
        "Czechia",
        "Česko",
        "Česká republika",
        "République tchèque",
        "Tschechien",
        "República Checa",
        "Repubblica Ceca",
    ],
    "Slovakia": ["Slovensko", "Slovaquie", "Eslovaquia", "Slowakei", "Slovacchia"],
    "Hungary": ["Magyarország", "Hongrie", "Hungría", "Ungarn", "Ungheria"],
    "Slovenia": ["Slovenija", "Slovénie", "Eslovenia", "Slowenien"],
    "Croatia": ["Hrvatska", "Croatie", "Croacia", "Kroatien", "Croazia"],
    "Serbia": ["Srbija", "Србија", "Serbie", "Serbien"],
    "Romania": ["România", "Roumanie", "Rumania", "Rumänien"],
    "Bulgaria": ["България", "Bulgarie", "Bulgarien"],
    "Greece": ["Ελλάδα", "Ελλάς", "Hellas", "Grèce", "Grecia", "Griechenland"],
    "Cyprus": ["Κύπρος", "Kıbrıs", "Chypre", "Chipre", "Zypern", "Cipro"],
    "Turkey": ["Türkiye", "Turquie", "Turquía", "Türkei", "Turchia"],
    "Georgia": ["საქართველო", "Sakartvelo", "Géorgie", "Georgien"],
    "Armenia": ["Հայաստան", "Hayastan", "Arménie", "Armenien"],
    "Moldova": ["Moldavie", "Moldavia", "Moldawien", "Republic of Moldova"],
    "Ukraine": ["Україна", "Ucrania", "Ucraina"],
    "Russia": ["Россия", "Rossiya", "Russie", "Rusia", "Russland"],
    "Lithuania": ["Lietuva", "Lituanie", "Lituania", "Litauen"],
    "Latvia": ["Latvija", "Lettonie", "Letonia", "Lettland"],
    "Estonia": ["Eesti", "Estonie", "Estland"],
    "Israel": ["ישראל", "Israël"],
    "Lebanon": ["لبنان", "Liban", "Líbano", "Libanon"],
    "Japan": ["日本", "Nippon", "Nihon", "Japon", "Giappone", "Japão"],
    "China": ["中国", "中國", "Chine", "Cina"],
    "Taiwan": ["台灣", "臺灣", "台湾"],
    "South Korea": [
        "대한민국",
        "한국",
        "Korea",
        "Republic of Korea",
        "Corée du Sud",
        "Corea del Sur",
        "Südkorea",
        "Corea del Sud",
    ],
    "Thailand": ["ประเทศไทย", "Thaïlande", "Tailandia"],
    "Vietnam": ["Việt Nam", "Viet Nam"],
    "Philippines": ["Pilipinas", "Filipinas"],
    "India": ["भारत", "Bharat", "Inde", "Indien"],
    "Australia": ["Australie", "Australien"],
    "New Zealand": ["Aotearoa", "Nouvelle-Zélande", "Nueva Zelanda", "Neuseeland"],
    "South Africa": ["Suid-Afrika", "Afrique du Sud", "Sudáfrica", "Südafrika"],
    "Argentina": ["Argentine", "Argentinien"],
    "Chile": ["Chili"],
    "Brazil": ["Brasil", "Brésil", "Brasilien"],
    "Uruguay": [],
    "Peru": ["Perú", "Pérou"],
    "Colombia": ["Colombie", "Kolumbien"],
    "Venezuela": [],
    "Panama": ["Panamá"],
    "Costa Rica": [],
    "Guatemala": [],
    "Nicaragua": [],
    "Cuba": [],
    "Jamaica": ["Jamaïque"],
    "Barbados": ["Barbade"],
    "Trinidad and Tobago": ["Trinidad & Tobago", "Trinité-et-Tobago"],
    "Dominican Republic": ["República Dominicana", "République dominicaine"],
    "Haiti": ["Haïti", "Ayiti"],
    "Guyana": [],
    "Belize": [],
}

# Places that belong to a country in the table.
PARENTS = {
    "Scotland": "United Kingdom",
    "England": "United Kingdom",
    "Wales": "United Kingdom",
    "Northern Ireland": "United Kingdom",
    "Puerto Rico": "United States",
    "U.S. Virgin Islands": "United States",
}


def match_key(text: str) -> str:
    """Lower case, no accents, no periods (U.S.A. becomes usa), other punctuation as spaces."""
    text = unicodedata.normalize("NFD", tidy(text).casefold())
    text = "".join(c for c in text if not unicodedata.combining(c)).replace(".", "")
    text = "".join(" " if unicodedata.category(c).startswith("P") else c for c in text)
    return " ".join(text.replace("&", " and ").split())


def alias_pattern(alias: str) -> re.Pattern:
    key = re.escape(match_key(alias))
    if non_latin_script(alias):
        return re.compile(key)  # these scripts don't always put spaces between words
    return re.compile(rf"(?<![^\W_]){key}(?![^\W_])")


# Longest names first, so "Northern Ireland" is found before "Ireland".
ALIASES = sorted(
    (
        (alias_pattern(name), name, country)
        for country, others in COUNTRY_NAMES.items()
        for name in [country, *others]
    ),
    key=lambda item: -len(item[1]),
)


def find_countries(text: str) -> list[tuple[str, str]]:
    """Countries named in the text, as (country, the name used). Places inside a
    country that is also named are kept and the country dropped."""
    remaining = match_key(text)
    found: dict[str, str] = {}
    for pattern, name, country in ALIASES:
        if pattern.search(remaining):
            found.setdefault(country, name)
            remaining = pattern.sub(" | ", remaining)
    parents = {PARENTS.get(country) for country in found}
    return [(country, name) for country, name in found.items() if country not in parents]


def is_us(country: str) -> bool:
    return country == "United States" or PARENTS.get(country) == "United States"


def is_domestic(country_text: str) -> bool:
    """True when no country is given, or it is the United States or a US territory."""
    if not tidy(country_text):
        return True
    found = find_countries(country_text)
    return len(found) == 1 and is_us(found[0][0])


def same_country(a: str, b: str) -> bool:
    """The same country, or a place within it: Scotland is in the United Kingdom."""
    return a == b or PARENTS.get(a) == b or PARENTS.get(b) == a


def check_country(
    application: str, label: FieldReading, bottler: FieldReading | None = None
) -> Check:
    """Compare the country of origin. `bottler` is the bottler or importer statement: a
    label sometimes names the country only there, as in "Distilled and bottled in Scotland"."""
    said = tidy(application)
    if is_missing(label) and said and not is_domestic(said) and bottler is not None:
        in_statement = only_in_bottler(said, bottler)
        if in_statement:
            return in_statement
    if is_missing(label):
        if not said:
            return Check(
                Status.NOT_NEEDED,
                "The application lists no country of origin, so this is a domestic product.",
            )
        if is_domestic(said):
            return Check(
                Status.NOT_NEEDED,
                f"The application says {said}, so this is a domestic product and needs no "
                "country of origin on the label.",
            )
        return Check(
            Status.FAIL,
            f"The label doesn't show the country of origin. The application says {said}, "
            "and imports must show it.",
        )
    shown = tidy(label.text or "")
    if is_unclear(label):
        return Check(
            Status.REVIEW,
            "Part of the country of origin is hard to read on the label. Please check it by eye.",
        )

    on_label = find_countries(shown)
    from_translation = False
    if not on_label and label.english_meaning:
        on_label = find_countries(label.english_meaning)
        from_translation = bool(on_label)
    if not on_label:
        return Check(
            Status.REVIEW, f'Couldn\'t tell which country "{shown}" names. Please check it by eye.'
        )
    if len(on_label) > 1:
        return Check(
            Status.REVIEW,
            f'The label names more than one country ("{shown}"). Please check it by eye.',
        )
    label_country, label_name = on_label[0]

    if not said:
        if is_us(label_country):
            return Check(Status.NOT_NEEDED, f'Domestic product. The label says "{shown}".')
        return Check(
            Status.REVIEW,
            f'The label says "{shown}", but the application lists no country of origin.',
        )
    on_application = find_countries(said)
    if len(on_application) != 1:
        return Check(
            Status.REVIEW,
            f"Couldn't tell which country the application's \"{said}\" names. "
            "Please check it by eye.",
        )
    application_country, application_name = on_application[0]

    if from_translation:
        return Check(
            Status.REVIEW,
            f'The label says "{shown}", which the AI reads as {label_country}. '
            f"The application says {said}. Please check by eye.",
        )
    if label_country == application_country:
        if match_key(label_name) == match_key(application_name):
            return Check(Status.PASS, "The country of origin matches the application.")
        return Check(
            Status.PASS,
            f'The label says "{shown}" and the application says "{said}". '
            f"Both mean {label_country}.",
            note=f"Matches, {label_name} = {application_name}",
        )
    for place, country in (
        (label_country, application_country),
        (application_country, label_country),
    ):
        if PARENTS.get(place) == country:
            return Check(
                Status.PASS,
                f'The label says "{shown}" and the application says "{said}". '
                f"{place} is part of the {country}.",
                note=f"Matches, {place} is part of the {country}",
            )
    return Check(Status.FAIL, f'The label says "{shown}" but the application says "{said}".')


def only_in_bottler(said: str, bottler: FieldReading) -> Check | None:
    """When the label has no country of origin statement but the bottler or importer
    statement names the application's country, a person should look: whether that is a
    clear enough statement of origin is a judgment, so it is never a plain match."""
    text = tidy(bottler.text or "")
    on_application = find_countries(said)
    if is_missing(bottler) or len(on_application) != 1:
        return None
    wanted = on_application[0][0]
    named = [country for country, _ in find_countries(text)]
    if not any(same_country(country, wanted) for country in named):
        return None
    return Check(
        Status.REVIEW,
        f'The label names {wanted} only in the bottler or importer statement ("{text}"), not '
        "in a country of origin statement. Please check it shows the country of origin clearly.",
    )
