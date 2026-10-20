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
  ttb_noted       the fields named by a condition in TTB's qualifications on the approval,
                  such as a statement to correct when new labels are printed
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
# How a planted problem was caught: by the comparison with the application (detected), or
# flagged for something else, such as print too hard to read.
HOW = {
    "comparison fail": "detected, shown as Problem",
    "comparison review": "detected, shown as Check this",
    "other fail": "shown as Problem for another reason",
    "other review": "sent to review for another reason",
    "pass": "missed, shown as Matches",
}
FIELD_TITLES = {
    "brand_name": "Brand name",
    "class_type": "Class or type",
    "alcohol_content": "Alcohol content",
    "net_contents": "Net contents",
    "bottler_name_address": "Bottler or importer",
    "country_of_origin": "Country of origin",
}
WORDS = {"fail": "Problem", "review": "Check this", "pass": "Matches", "pass_with_note": "Matches"}
FLAGGED = {"fail", "review"}


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
    # Planted problems are made up, so their results are published label by label: they
    # say nothing about the real labels' own flaws.
    planted_rows = []
    for record in planted:
        case = by_id[record["id"]]
        field = case["planted_field"]
        how = HOW[record["causes"][field]] if "causes" in record else None
        planted_rows.append(
            {
                "ttb_id": case["ttb_id"],
                "field": field,
                "result": record["got"].get(field, ""),
                "how": how,
            }
        )
    planted_rows.sort(key=lambda row: row["ttb_id"])
    # Issues flagged on the labels as approved, and the fields TTB's qualifications name.
    approved = [r for r in scored if by_id[r["id"]]["kind"] == "as approved"]
    flagged = Counter()
    noted, both = 0, 0
    for record in approved:
        named = set(by_id[record["id"]].get("ttb_noted", []))
        noted += len(named)
        for field, word in record["got"].items():
            if word in FLAGGED:
                flagged[word] += 1
                both += field in named
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
        "planted_how": dict(Counter(row["how"] for row in planted_rows if row["how"])),
        "planted_rows": planted_rows,
        "flagged_as_problem": flagged["fail"],
        "flagged_as_check_this": flagged["review"],
        "ttb_noted": noted,
        "flagged_and_ttb_noted": both,
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
    flagged = totals["flagged_as_problem"] + totals["flagged_as_check_this"]
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
        *[
            (f"Planted problems {how}", totals["planted_how"].get(how, 0))
            for how in HOW.values()
            if totals["planted_how"]
        ],
        (
            "Issues flagged on the labels as approved",
            f"{flagged}: {totals['flagged_as_problem']} Problem, "
            f"{totals['flagged_as_check_this']} Check this",
        ),
        (
            "Of those, on a field TTB's qualifications name",
            f"{totals['flagged_and_ttb_noted']} of {flagged}",
        ),
        (
            "Fields TTB's qualifications name, flagged by the tool",
            f"{totals['flagged_and_ttb_noted']} of {totals['ttb_noted']}",
        ),
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
        "Some approvals carry qualifications: TTB approved the label and noted a condition, such "
        "as a statement to correct when new labels are printed. The fields each condition names "
        "were written down before the run. Conditions about things the tool doesn't check, and "
        "TTB's standard note that it didn't review type size or contrast, aren't counted.",
        "",
        "| Measure | Result |",
        "|---|---|",
        *[f"| {measure} | {result} |" for measure, result in rows],
        "",
        *planted_table(totals),
        "## TTB IDs",
        "",
        "Each can be looked up in the registry. They are listed in order of ID, not of results.",
        "",
        *[f"- {ttb_id}" for ttb_id in totals["ttb_ids"]],
    ]
    return "\n".join(lines) + "\n"


def planted_table(totals: dict) -> list[str]:
    """The planted problems label by label. A planted problem is a made-up change to the
    application, so this says nothing about the real labels' own results."""
    if not totals["planted_rows"]:
        return []
    detailed = any(row["how"] for row in totals["planted_rows"])
    lines = [
        "## Planted problems, label by label",
        "",
        "Each label was checked a second time with one field of its application changed to a "
        "wrong value. These made-up problems are published label by label; the real labels' own "
        "results are not. **Detected** means the field's comparison with the application raised "
        "it; **another reason** means the field was flagged for something else, such as print "
        "too hard to read.",
        "",
        "| TTB ID | Field changed | Result | How |"
        if detailed
        else "| TTB ID | Field changed | Result |",
        "|---|---|---|---|" if detailed else "|---|---|---|",
    ]
    for row in totals["planted_rows"]:
        cells = [row["ttb_id"], FIELD_TITLES[row["field"]], WORDS.get(row["result"], row["result"])]
        if detailed:
            cells.append(row["how"] or "")
        lines.append("| " + " | ".join(cells) + " |")
    return [*lines, ""]
