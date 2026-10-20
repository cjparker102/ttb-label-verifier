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
    """Totals only. Nothing in here can be traced to one label."""
    by_id = {case["id"]: case for case in cases}
    scored = [r for r in results["records"] if "judgments" in r]
    approved = [r for r in scored if by_id[r["id"]]["kind"] == "as approved"]
    planted = [r for r in scored if by_id[r["id"]]["kind"] == "planted"]
    caught = Counter(r["judgments"][by_id[r["id"]]["planted_field"]] for r in planted)
    labels = {case["ttb_id"]: case["beverage_type"] for case in cases}
    return {
        "labels": len(labels),
        "by_type": dict(Counter(KINDS[kind] for kind in labels.values())),
        "checks": len(results["records"]),
        "errors": summary["errors"],
        "read_by_ocr": summary["read_by_ocr"],
        "fields": summary["fields"],
        "judgments": summary["judgments"],
        "approved_all_fine": sum(1 for r in approved if set(r["judgments"].values()) <= FINE),
        "approved": len(approved),
        "approved_false_fails": sum(
            1 for r in approved for j in r["judgments"].values() if j == "false_fail"
        ),
        "approved_extra_reviews": sum(
            1 for r in approved for j in r["judgments"].values() if j == "extra_review"
        ),
        "planted": len(planted),
        "planted_caught_as_problem": caught["exact"],
        "planted_caught_as_check_this": caught["review_instead_of_fail"],
        "planted_missed": caught["false_pass"],
        "seconds": summary.get("seconds"),
        "cost_usd": summary.get("cost_usd"),
        "ttb_ids": sorted(labels),
    }


def public_markdown(results: dict, totals: dict) -> str:
    kinds = ", ".join(f"{n} {kind}" for kind, n in sorted(totals["by_type"].items()))
    rows = [
        ("Labels", f"{totals['labels']} ({kinds})"),
        ("Checks", f"{totals['checks']}: each label as approved, and with one planted problem"),
        ("Errors", totals["errors"]),
        ("Labels read with basic text reading", totals["read_by_ocr"]),
        (
            "As approved: labels with every field as expected",
            f"{totals['approved_all_fine']} of {totals['approved']}",
        ),
        ("As approved: false Problems (fields)", totals["approved_false_fails"]),
        ("As approved: extra Check this (fields)", totals["approved_extra_reviews"]),
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
    kinds_of_result = ", ".join(
        f"{kind.replace('_', ' ')} {n}" for kind, n in sorted(totals["judgments"].items())
    )
    lines = [
        f"# Real labels from the COLA Registry, {results['measured_at'][:10]}",
        "",
        "Approved labels from TTB's Public COLA Registry, checked in process with the app's "
        f"own code. Commit: `{results['commit']}`. Settings: `{results['settings']}`.",
        "",
        "The pictures, the application data, the answer key, and the result for each label are "
        "kept private. Only these totals and the TTB IDs are published.",
        "",
        "| Measure | Result |",
        "|---|---|",
        *[f"| {measure} | {result} |" for measure, result in rows],
        "",
        f"All {totals['fields']} field results by kind: {kinds_of_result}.",
        "",
        "## TTB IDs",
        "",
        "Each can be looked up in the registry. They are listed in order of ID, not of results.",
        "",
        *[f"- {ttb_id}" for ttb_id in totals["ttb_ids"]],
    ]
    return "\n".join(lines) + "\n"
