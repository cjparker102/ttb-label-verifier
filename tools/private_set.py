"""A private set of real labels for tools/evaluate.py, such as approved labels from TTB's
Public COLA Registry. The set lives in private/, which is never committed, because it
holds label pictures, label text, and application data. Only totals and the TTB IDs are
published, never a result for any one label.

The set is a JSON file listing cases. Each label is checked twice: as approved, and with
one problem planted in its application data. A case has:
  id              unique, for example "26002001000021" or "26002001000021-planted"
  ttb_id          the label's TTB ID in the registry
  kind            "as approved" or "planted"
  planted_field   for a planted case, the field that was changed
  beverage_type   distilled_spirits, wine, or malt_beverage
  application     the application data, field by field
  images          picture files, relative to the JSON file
  expected        the right result for each field; a list where more than one is right
"""

import json
import subprocess
from collections import Counter
from pathlib import Path

KINDS = {
    "distilled_spirits": "distilled spirits",
    "wine": "wine",
    "malt_beverage": "malt beverages",
}
FINE = {"exact", "note_difference"}


class NotPrivate(Exception):
    """The set is in a folder git would commit."""


def load_cases(path: Path) -> list[dict]:
    ignored = subprocess.run(["git", "check-ignore", "-q", str(path)], check=False)
    if ignored.returncode != 0:
        raise NotPrivate(f"{path} is not in a folder git ignores, such as private/.")
    cases = json.loads(path.read_text(encoding="utf-8"))
    for case in cases:
        case["folder"] = str(path.parent)
        case.setdefault("photo", None)
    return cases


def public_summary(cases: list[dict], results: dict, summary: dict) -> dict:
    """Totals only. Nothing in here can be traced to one label. Accuracy is given twice,
    never combined: strict, on fields with one right answer, and judgment calls, on
    fields where the answer key accepts two."""
    by_id = {case["id"]: case for case in cases}
    scored = [r for r in results["records"] if "judgments" in r]
    strict, judgment = Counter(), Counter()
    for record in scored:
        expected = by_id[record["id"]]["expected"]
        for field, verdict in record["judgments"].items():
            (judgment if isinstance(expected[field], list) else strict)[verdict] += 1
    planted = [r for r in scored if by_id[r["id"]]["kind"] == "planted"]
    caught = Counter(r["judgments"][by_id[r["id"]]["planted_field"]] for r in planted)
    labels = {case["ttb_id"]: case["beverage_type"] for case in cases}
    return {
        "labels": len(labels),
        "by_type": dict(Counter(KINDS[kind] for kind in labels.values())),
        "checks": len(results["records"]),
        "errors": summary["errors"],
        "read_by_ocr": summary["read_by_ocr"],
        "strict": dict(strict),
        "judgment": dict(judgment),
        "planted": len(planted),
        "planted_caught_as_problem": caught["exact"],
        "planted_caught_as_check_this": caught["review_instead_of_fail"],
        "planted_missed": caught["false_pass"],
        "seconds": summary.get("seconds"),
        "cost_usd": summary.get("cost_usd"),
        "ttb_ids": sorted(labels),
    }


def as_expected(verdicts: dict) -> str:
    """How many fields came out right, of how many. "Matches, with a note" counts as Matches."""
    right = sum(n for verdict, n in verdicts.items() if verdict in FINE)
    return f"{right} of {sum(verdicts.values())}"


def the_rest(verdicts: dict) -> str:
    wrong = {v: n for v, n in sorted(verdicts.items()) if v not in FINE}
    return ", ".join(f"{v.replace('_', ' ')} {n}" for v, n in wrong.items()) or "none"


def public_markdown(results: dict, totals: dict) -> str:
    kinds = ", ".join(f"{n} {kind}" for kind, n in sorted(totals["by_type"].items()))
    strict, judgment = totals["strict"], totals["judgment"]
    rows = [
        ("Labels", f"{totals['labels']} ({kinds})"),
        ("Checks", f"{totals['checks']}: each label as approved, and with one planted problem"),
        ("Errors", totals["errors"]),
        ("Labels read with basic text reading", totals["read_by_ocr"]),
        ("**Strict:** fields with one right answer, as expected", as_expected(strict)),
        ("Strict: the others", the_rest(strict)),
        (
            "**Judgment calls:** fields where two answers are right, either given",
            as_expected(judgment),
        ),
        ("Judgment calls: the others", the_rest(judgment)),
        (
            "Planted problems shown as Problem",
            f"{totals['planted_caught_as_problem']} of {totals['planted']}",
        ),
        ("Planted problems shown as Check this", totals["planted_caught_as_check_this"]),
        ("Planted problems missed (shown as Matches)", totals["planted_missed"]),
    ]
    if totals["seconds"]:
        s = totals["seconds"]
        rows.append(
            (
                "Time per check (median / p95 / max)",
                f"{s['median']} s / {s['p95']} s / {s['max']} s",
            )
        )
    if totals["cost_usd"] is not None:
        rows.append(("AI cost for this run (estimate from tokens)", f"${totals['cost_usd']}"))
    lines = [
        f"# Real labels from the COLA Registry, {results['measured_at'][:10]}",
        "",
        "Approved labels from TTB's Public COLA Registry, checked in process with the app's "
        f"own code. Commit: `{results['commit']}`. Settings: `{results['settings']}`.",
        "",
        "The pictures, the application data, the answer key, and the result for each label are "
        "kept private. Only these totals and the TTB IDs are published.",
        "",
        "Accuracy is given twice, never combined. **Strict** counts the fields with one right "
        "answer, including every planted problem. **Judgment calls** count the fields where the "
        "answer key accepts two answers, such as Matches or Check this for a warning whose body "
        "text looks bold.",
        "",
        "| Measure | Result |",
        "|---|---|",
        *[f"| {measure} | {result} |" for measure, result in rows],
        "",
        "## TTB IDs",
        "",
        "Each can be looked up in the registry. They are listed in order of ID, not of results.",
        "",
        *[f"- {ttb_id}" for ttb_id in totals["ttb_ids"]],
    ]
    return "\n".join(lines) + "\n"
