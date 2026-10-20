"""How often Tesseract's second reading of the warning is missing or inconclusive, on the
private sets of real labels. Replays the AI reader's saved warning for each label as
approved through the app's own check, with Tesseract run on the warning's picture. No AI
request is made, so it costs nothing. Only totals are published.

    uv run python -m tools.second_reading private/cola/cases.json:results-2026-10-20-2.json ...
"""

import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

from app.highlights import ocr_passes
from app.intake.images import shrink_to_jpeg, split_pages
from app.reading.schema import LabelReading
from app.rules.text import is_missing, tidy
from app.rules.warning import differences, tokens
from tools.evaluate import pictures_of
from tools.private_set import load_cases

OUT_DIR = Path(__file__).resolve().parent.parent / "docs" / "measurements"
MAX_EDGE = 1568


def outcome(reading: LabelReading, pictures: list[bytes]) -> str:
    """What the second reading made of one label's warning."""
    warning = reading.government_warning
    if is_missing(warning) or warning.image_number is None:
        return "no warning read by the AI reader"
    passes = ocr_passes([pictures[warning.image_number - 1]])[0]
    found = tokens(tidy(warning.text or ""))
    readings = [differences(found, tokens(" ".join(w.text for w in words))) for words in passes]
    read = [r for r in readings if r is not None]
    if not read:
        return "missing: neither pass read the warning"
    if len(read) < len(readings):
        return "missing: one pass read the warning, the other didn't"
    if set.intersection(*(set(r) for r in read)):
        return "both passes read it, and disagreed with the AI reader"
    if any(read):
        return "both passes read it; only one disagreed (taken for a misreading)"
    return "both passes read it, and agreed with the AI reader"


def main() -> None:
    import json

    counts: Counter[str] = Counter()
    labels = 0
    for argument in sys.argv[1:]:
        cases_path, results_name = argument.split(":")
        cases = [c for c in load_cases(Path(cases_path)) if c["kind"] == "as approved"]
        saved = json.loads((Path(cases_path).parent / results_name).read_text(encoding="utf-8"))
        readings = {r["id"]: r["reading"] for r in saved["records"] if "reading" in r}
        for case in cases:
            pictures = [
                shrink_to_jpeg(data, MAX_EDGE)
                for name, picture in pictures_of(case)
                for _, data in split_pages(name, picture)
            ]
            counts[outcome(LabelReading.model_validate(readings[case["id"]]), pictures)] += 1
            labels += 1
    lines = [
        f"# The warning's second reading on real labels, {datetime.now():%Y-%m-%d}",
        "",
        f"{labels} approved labels from TTB's Public COLA Registry (the three private sets), each "
        "label's saved reading by Claude replayed with the app's own check, and Tesseract run on "
        "the picture with the warning, as in a batch. No AI request was made. Measured with "
        "`tools/second_reading.py`; only totals are published.",
        "",
        "| What the second reading made of the warning | Labels |",
        "|---|---|",
        *[f"| {kind} | {n} |" for kind, n in counts.most_common()],
        f"| **All** | **{labels}** |",
    ]
    out = OUT_DIR / f"second-reading-{datetime.now():%Y-%m-%d}.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
