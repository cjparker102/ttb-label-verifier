"""The code-side bold check at several settings: how often each would add Check this.

The AI reader says whether "GOVERNMENT WARNING" looks bold, and can be wrong. Bold type
has thicker strokes than the same type set normally. Tesseract says where each word is, so
app/reading/strokes.py measures the strokes of the heading's words and of the warning's
words after it, on the same picture. This asks how often "heading not clearly heavier"
would add Check this at each setting (the app uses 1.1 times, on print at least 14 pixels):
on the samples, and on the private real labels, with each label's saved reading by Claude
(which picture has the warning, and whether Claude called the heading bold). No AI request
is made, so it costs nothing. Only totals are published for the real labels.

    uv run python -m tools.heading_weight --not-bold private/not-bold.txt \
        private/cola/cases.json:results-2026-10-20-2.json ...
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

from app.highlights import ocr_passes
from app.intake.images import shrink_to_jpeg, split_pages
from app.reading.strokes import heading_weight
from tools.evaluate import load_entries, pictures_of
from tools.private_set import load_cases

OUT_DIR = Path(__file__).resolve().parent.parent / "docs" / "measurements"
SAMPLE_READINGS = OUT_DIR / "evaluation-2026-10-20-anthropic-3.json"
MAX_EDGE = 1568
THRESHOLDS = (1.0, 1.05, 1.1, 1.15, 1.2)  # "clearly heavier" means at least this ratio
MIN_HEIGHTS = (0, 14)  # pixels: leave out headings printed smaller than this


def measure(entry: dict, reading: dict) -> tuple[float, float] | None:
    """The heading's weight on the picture the AI reader found the warning on."""
    number = (reading.get("government_warning") or {}).get("image_number")
    pictures = [
        shrink_to_jpeg(data, MAX_EDGE)
        for name, picture in pictures_of(entry)
        for _, data in split_pages(name, picture)
    ]
    if not number or not 0 < number <= len(pictures):
        return None
    picture = pictures[number - 1]
    weight = heading_weight(picture, ocr_passes([picture])[0])
    return (weight.ratio, weight.height) if weight else None


def flagged(rows: list[dict], threshold: float, min_height: float) -> list[dict]:
    """Labels the check would send to review: Claude called the heading bold (otherwise it
    is Check this already), and it measured less than `threshold` times heavier."""
    return [
        row
        for row in rows
        if row["ai_bold"] == "yes"
        and row["weight"]
        and row["weight"][1] >= min_height
        and row["weight"][0] < threshold
    ]


def cell(rows: list[dict]) -> str:
    """How many were flagged, and for real labels with a bold heading, how many of those
    the answer key says are Matches, so the flag would make the result wrong."""
    wrong = sum(1 for row in rows if row.get("key_says_matches"))
    return (
        f"{len(rows)} ({wrong} wrong)"
        if any("key_says_matches" in r for r in rows)
        else str(len(rows))
    )


def table(groups: dict[str, list[dict]]) -> list[str]:
    lines = [
        "| Clearly heavier means | Print at least | "
        + " | ".join(f"{name} ({len(rows)})" for name, rows in groups.items())
        + " |",
        "|---|---|" + "---|" * len(groups),
    ]
    for threshold in THRESHOLDS:
        for height in MIN_HEIGHTS:
            cells = [cell(flagged(rows, threshold, height)) for rows in groups.values()]
            shown = f"{height} px" if height else "any size"
            lines.append(f"| {threshold:g} times | {shown} | " + " | ".join(cells) + " |")
    return lines


def counts(rows: list[dict]) -> str:
    said = sum(row["ai_bold"] == "yes" for row in rows)
    measured = [row["weight"][0] for row in rows if row["weight"]]
    shown = ", ".join(f"{w:.2f}" for w in sorted(measured)[:6])
    return (
        f"{len(rows)} labels; Claude called {said} bold; {len(measured)} measured, whatever "
        f"Claude said (lowest: {shown or 'none'})"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--not-bold", required=True, help="private list of TTB IDs, one a line")
    parser.add_argument("sets", nargs="+", help="cases.json:results.json, for each private set")
    args = parser.parse_args()
    not_bold = {
        line.strip()
        for line in Path(args.not_bold).read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    }
    saved = {r["id"]: r["reading"] for r in json.loads(SAMPLE_READINGS.read_text())["records"]}
    samples = {"bold": [], "not bold": []}
    for entry in load_entries(None):
        bold = (entry["truth"].get("government_warning") or {}).get("heading_bold")
        if bold is None or entry["id"] not in saved:
            continue  # no warning on the label
        reading = saved[entry["id"]]
        row = {"ai_bold": reading["government_warning"]["heading_bold"]}
        row["weight"] = measure(entry, reading)
        samples["bold" if bold else "not bold"].append(row)
        print(entry["id"], row, flush=True)
    real = {"bold": [], "not bold": []}
    for argument in args.sets:
        cases_path, results_name = argument.split(":")
        cases = [c for c in load_cases(Path(cases_path)) if c["kind"] == "as approved"]
        results = json.loads((Path(cases_path).parent / results_name).read_text(encoding="utf-8"))
        readings = {r["id"]: r["reading"] for r in results["records"] if "reading" in r}
        for case in cases:
            reading = readings[case["id"]]
            row = {"ai_bold": reading["government_warning"]["heading_bold"]}
            row["weight"] = measure(case, reading)
            if case["ttb_id"] in not_bold:
                real["not bold"].append(row)
            else:
                row["key_says_matches"] = case["expected"]["government_warning"] == "pass"
                real["bold"].append(row)
    groups = {
        "Samples, not bold": samples["not bold"],
        "Samples, bold": samples["bold"],
        "Real, not bold": real["not bold"],
        "Real, bold": real["bold"],
    }
    lines = [
        f"# A code-side bold check, measured, {datetime.now():%Y-%m-%d}",
        "",
        "The stroke thickness of the warning's heading against the warning's words after it, "
        "measured on the picture where Tesseract found both. The check would add Check this "
        "when Claude calls the heading bold but it measures less than clearly heavier; when "
        "Claude doesn't call it bold, it is Check this already. Each label's saved reading by "
        "Claude was used; no AI request was made. Real labels: the four private sets as "
        "approved, with the headings the answer keys say aren't bold. Measured with "
        "`tools/heading_weight.py`; only totals are published.",
        "",
        *[f"- {name}: {counts(rows)}" for name, rows in groups.items()],
        "",
        "Labels the check would send to review. With a bold heading, each one is a false alarm "
        'about the heading. For real labels, "wrong" counts those whose answer key says '
        "Matches for the warning, so the flag would make the result wrong; the others' keys "
        "accept Check this for another reason, such as a small picture.",
        "",
        *table(groups),
    ]
    out = OUT_DIR / f"heading-weight-{datetime.now():%Y-%m-%d}.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
