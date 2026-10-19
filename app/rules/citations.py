"""The eCFR paragraphs behind each TTB check.

Each section was read in the eCFR on Oct 19, 2026 (Title 27 up to date as of
Oct 15, 2026) before the check that cites it was written.
"""

from app.rules.results import Citation

CHECKED = "2026-10-19"


def ecfr(section: str, paragraph: str = "") -> Citation:
    url = f"https://www.ecfr.gov/current/title-27/section-{section}"
    if paragraph:
        url += f"#p-{section}{paragraph}"
    return Citation(f"27 CFR {section}{paragraph}", url, CHECKED)


WARNING_TEXT = ecfr("16.21")
WARNING_FORMAT = ecfr("16.22", "(a)(2)")

SPIRITS_SAME_SIDE = ecfr("5.63", "(a)")
SPIRITS_ALCOHOL_REQUIRED = ecfr("5.63", "(a)(3)")
SPIRITS_ALCOHOL_FORM = ecfr("5.65", "(b)")
SPIRITS_NET_CONTENTS = ecfr("5.70", "(a)")
SPIRITS_SIZES = ecfr("5.203", "(a)")
SPIRITS_BOTTLER = ecfr("5.66", "(b)")
SPIRITS_IMPORTER = ecfr("5.68", "(b)")
SPIRITS_ENGLISH = ecfr("5.55", "(a)")

WINE_ALCOHOL_REQUIRED = ecfr("4.36", "(a)")
WINE_ALCOHOL_FORM = ecfr("4.36", "(b)")
WINE_NET_CONTENTS = ecfr("4.37", "(a)")
WINE_SIZES = ecfr("4.72")
WINE_BOTTLER = ecfr("4.35", "(a)(1)")
WINE_IMPORTER = ecfr("4.35", "(b)(1)")
WINE_ENGLISH = ecfr("4.38", "(c)")

MALT_ALCOHOL_REQUIRED = ecfr("7.63", "(a)(3)")
MALT_ALCOHOL_FORM = ecfr("7.65", "(b)")
MALT_NET_CONTENTS = ecfr("7.70")
MALT_IMPORTER = ecfr("7.68", "(b)")
MALT_ENGLISH = ecfr("7.55", "(a)")
