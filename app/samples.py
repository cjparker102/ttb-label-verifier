"""The sample labels reviewers can try with one click (samples/ in this repository).

Each sample is a made-up label with a known problem planted in it. Its application
data comes from samples/applications.csv, read with the same code that reads any
uploaded spreadsheet.
"""

import json
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from app.intake.spreadsheet import ApplicationRow, read_spreadsheet

SAMPLES_DIR = Path(__file__).resolve().parent.parent / "samples"

# The samples shown as buttons, in this order, with plain titles.
FEATURED = {
    "old-tom-bourbon": "A clean bourbon label, front and back",
    "ridgewick-rye-wrong-abv": "Alcohol content that doesn't match",
    "copperfen-vodka-title-case-warning": "Warning heading not in capitals",
    "chateau-landrevin-wine": "Imported French wine with accents",
    "heronmere-gin-warning-wording--blurry": "A blurry photo with a changed warning",
    "granitefall-bourbon-prompt-injection": "A label that tries to trick the AI",
}


@dataclass(frozen=True)
class SampleLabel:
    id: str
    title: str
    planted: str  # what was planted, in plain words
    row: ApplicationRow
    images: tuple[str, ...]


@cache
def sample_labels() -> dict[str, SampleLabel]:
    """Every sample, by id. Empty if the samples folder isn't there."""
    try:
        expected = json.loads((SAMPLES_DIR / "expected.json").read_text(encoding="utf-8"))
        sheet = (SAMPLES_DIR / "applications.csv").read_bytes()
    except FileNotFoundError:
        return {}
    rows = {row.file_names: row for row in read_spreadsheet("applications.csv", sheet)}
    return {
        entry["id"]: SampleLabel(
            id=entry["id"],
            title=FEATURED.get(entry["id"], entry["id"]),
            planted=entry["planted"],
            row=rows[tuple(entry["images"])],
            images=tuple(entry["images"]),
        )
        for entry in expected
    }


def featured() -> list[SampleLabel]:
    labels = sample_labels()
    return [labels[sample_id] for sample_id in FEATURED if sample_id in labels]


def pictures(label: SampleLabel) -> list[tuple[str, bytes]]:
    return [(name, (SAMPLES_DIR / "labels" / name).read_bytes()) for name in label.images]
