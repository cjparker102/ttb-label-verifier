"""Turns check results into what the page shows: plain words, icons, and order."""

import base64
from collections import Counter
from dataclasses import dataclass
from io import BytesIO

from PIL import Image

from app.batch import BatchItem, BatchJob, ItemState
from app.checking import CheckOutcome
from app.photo_coach import photo_tips
from app.rules.application import BeverageType
from app.rules.results import Status, worst
from app.rules.text import tidy
from app.rules.verdict import FieldResult
from app.rules.warning import GOVERNMENT_WARNING, track_changes


@dataclass(frozen=True)
class TextField:
    name: str
    label: str
    hint: str
    required: bool = True


TEXT_FIELDS = [
    TextField(
        "brand_name", "Brand name", "As written in the application, for example OLD TOM DISTILLERY."
    ),
    TextField("class_type", "Class or type", "For example Kentucky Straight Bourbon Whiskey."),
    TextField(
        "alcohol_content",
        "Alcohol content",
        "For example 45% or 45% Alc./Vol. (90 Proof). Some beers and wines may leave it out.",
        required=False,
    ),
    TextField("net_contents", "Net contents", "For example 750 mL or 12 fl oz."),
    TextField(
        "bottler_name_address",
        "Bottler or importer name and address",
        "For example Old Tom Distillery, Bardstown, Kentucky.",
    ),
    TextField(
        "country_of_origin",
        "Country of origin",
        "Leave blank for products made in the United States.",
        required=False,
    ),
]

BEVERAGE_CHOICES = [
    (BeverageType.DISTILLED_SPIRITS.value, "Distilled spirits"),
    (BeverageType.WINE.value, "Wine"),
    (BeverageType.MALT_BEVERAGE.value, "Malt beverage (beer)"),
]

STATUS_VIEW = {
    Status.FAIL: {"icon": "❌", "word": "Problem", "css": "fail"},
    Status.REVIEW: {"icon": "⚠️", "word": "Check this", "css": "review"},
    Status.PASS: {"icon": "✅", "word": "Matches", "css": "pass"},
    Status.NOT_NEEDED: {"icon": "➖", "word": "Not needed", "css": "not-needed"},
}


def summary(counts) -> list[dict]:
    """The top line: Problems found (n), Needs review (n), or, if neither, no issues found."""
    lines = []
    if counts[Status.FAIL]:
        lines.append(
            {"css": "fail", "icon": "❌", "text": f"Problems found ({counts[Status.FAIL]})"}
        )
    if counts[Status.REVIEW]:
        lines.append(
            {"css": "review", "icon": "⚠️", "text": f"Needs review ({counts[Status.REVIEW]})"}
        )
    if not lines:
        lines.append({"css": "pass", "icon": "✅", "text": "No issues found in the checked fields"})
    return lines


RULE_RESULT = {
    Status.PASS: "met",
    Status.REVIEW: "check this",
    Status.FAIL: "not met",
    Status.NOT_NEEDED: "not needed",
}


def rules_checked(field: FieldResult) -> list[dict]:
    """Each eCFR section behind this field's checks, once, with its worst result."""
    by_section: dict[str, dict] = {}
    for check in field.checks:
        if check.citation is None:
            continue
        section = check.citation.section
        if section in by_section:
            by_section[section]["statuses"].append(check.status)
        else:
            by_section[section] = {"url": check.citation.url, "statuses": [check.status]}
    return [
        {"section": section, "url": rule["url"], "result": RULE_RESULT[worst(rule["statuses"])]}
        for section, rule in by_section.items()
    ]


def field_row(field: FieldResult) -> dict:
    status = field.status
    problems = [c for c in field.checks if c.status in (Status.FAIL, Status.REVIEW)]
    shown = problems or [field.checks[0]]
    word = STATUS_VIEW[status]["word"]
    if status == Status.PASS and field.notes:
        word = field.notes[0]
    return {
        "title": field.title,
        "is_warning": field.field == "government_warning",
        "application_says": field.application_says or "(blank)",
        "label_says": field.label_says,
        "image": f"Image {field.image_number}" if field.image_number else None,
        "view": STATUS_VIEW[status],
        "word": word,
        "reasons": [{"text": c.reason, "citation": c.citation} for c in shown],
        "rules": rules_checked(field),
        "track": warning_track(field),
    }


def warning_track(field: FieldResult) -> list[tuple[str, str]] | None:
    """A track-changes view of the warning, only when its wording differs."""
    if field.field != "government_warning" or not field.label_says:
        return None
    if not any(check.changes for check in field.checks):
        return None
    return track_changes(GOVERNMENT_WARNING, tidy(field.label_says))


def results_view(outcome: CheckOutcome) -> dict:
    numbers = {highlight.field: n for n, highlight in enumerate(outcome.highlights, start=1)}
    rows = [
        {**field_row(field), "outline": numbers.get(field.field)} for field in outcome.result.fields
    ]
    needs_attention = {"fail", "review"}
    return {
        "summary": summary(outcome.result.counts),
        "problem_rows": [r for r in rows if r["view"]["css"] in needs_attention],
        "ok_rows": [r for r in rows if r["view"]["css"] not in needs_attention],
        "seconds": f"{outcome.seconds:.1f}",
        "photo_tips": photo_tips(list(outcome.photo_problems)),
        # For measurements only: whether Tesseract's second reading was ready in time.
        "second_reading": "yes" if outcome.second_reading else "no",
    }


def picture_views(outcome: CheckOutcome, previews: list[str]) -> list[dict]:
    """Each checked picture with the outlines on it. Outlines are measured in the
    checked picture's pixels; the preview is a smaller copy with the same shape."""
    views = []
    for number, (picture, src) in enumerate(zip(outcome.images, previews, strict=True), start=1):
        with Image.open(BytesIO(picture)) as image:
            width, height = image.size
        tag = max(width, height) // 20  # the size of the number tag on each outline
        boxes = []
        for n, highlight in enumerate(outcome.highlights, start=1):
            if highlight.image_number != number:
                continue
            x, y = highlight.left, highlight.top
            boxes.append(
                {
                    "number": n,
                    "title": highlight.title,
                    **STATUS_VIEW[highlight.status],
                    "x": x,
                    "y": y,
                    "width": highlight.width,
                    "height": highlight.height,
                    # The tag sits on the outline's top-left corner, inside the picture.
                    "tag_x": min(x, width - tag),
                    "tag_y": y - tag if y >= tag else y,
                }
            )
        views.append(
            {
                "number": number,
                "src": src,
                "width": width,
                "height": height,
                "tag": tag,
                "boxes": boxes,
            }
        )
    return views


def data_uri(jpeg: bytes) -> str:
    return "data:image/jpeg;base64," + base64.b64encode(jpeg).decode("ascii")


# Batch labels, problems first.
ITEM_ORDER = {"fail": 0, "not-checked": 1, "review": 2, "waiting": 3, "pass": 4}


def labels(count: int) -> str:
    return f"{count} label{'s' if count != 1 else ''}"


def item_view(item: BatchItem) -> dict:
    view = {
        "row_number": item.row_number,
        "brand": item.brand or "(no brand name)",
        "files": ", ".join(item.file_names),
        "previews": len(item.previews),
        "read_by_ocr": False,
        "reasons": [],
        "fields": [],
    }
    if item.state == ItemState.WAITING:
        return {**view, "kind": "waiting", "icon": "⏳", "word": "Waiting"}
    if item.state == ItemState.NOT_CHECKED or item.outcome is None:
        return {
            **view,
            "kind": "not-checked",
            "icon": "⛔",
            "word": "Not checked",
            "reasons": [item.problem or ""],
        }
    result = item.outcome.result
    lines = summary(result.counts)
    return {
        **view,
        "read_by_ocr": item.outcome.read_by == "ocr",
        "photo_tips": photo_tips(list(item.outcome.photo_problems)),
        "kind": lines[0]["css"],
        "icon": lines[0]["icon"],
        "word": " / ".join(line["text"] for line in lines),
        "reasons": [
            f"{field.title}: {check.reason}"
            for field in result.fields
            for check in field.checks
            if check.status in (Status.FAIL, Status.REVIEW)
        ],
        "fields": [field_row(field) for field in result.fields],
    }


def batch_view(job: BatchJob) -> dict:
    items = sorted(
        (item_view(item) for item in job.items),
        key=lambda view: (ITEM_ORDER[view["kind"]], view["row_number"]),
    )
    count = Counter(view["kind"] for view in items)
    lines = []
    if count["fail"]:
        lines.append(
            {"css": "fail", "icon": "❌", "text": f"Problems found in {labels(count['fail'])}"}
        )
    if count["review"]:
        verb = "needs" if count["review"] == 1 else "need"
        lines.append(
            {"css": "review", "icon": "⚠️", "text": f"{labels(count['review'])} {verb} review"}
        )
    if count["not-checked"]:
        lines.append(
            {
                "css": "not-checked",
                "icon": "⛔",
                "text": f"{labels(count['not-checked'])} could not be checked",
            }
        )
    if count["pass"]:
        lines.append(
            {
                "css": "pass",
                "icon": "✅",
                "text": f"{labels(count['pass'])} with no issues found in the checked fields",
            }
        )
    finished = job.state == "finished"
    timing = None
    checked = sum(1 for item in job.items if item.state == ItemState.DONE)
    if finished and checked and job.started_at is not None and job.finished_at is not None:
        total = job.finished_at - job.started_at
        timing = (
            f"Checked {labels(checked)} in {total:.0f} seconds, about {total / checked:.1f} "
            "seconds a label."
        )
    return {
        "job_id": job.id,
        "state": job.state,
        "finished": finished,
        "done": job.done,
        "total": job.total,
        "batch_summary": lines,
        # While a batch runs, show only the problems found so far, to keep updates small.
        "items": items if finished else [v for v in items if v["kind"] not in ("pass", "waiting")],
        "passed_so_far": count["pass"],
        "read_by_ocr": sum(1 for view in items if view["read_by_ocr"]),
        "notes": job.notes,
        # The batch as a whole: a label's own time would include waiting for other labels.
        "timing": timing,
        "skipped": job.skipped_files,
        "unused": job.unused_pictures,
    }
