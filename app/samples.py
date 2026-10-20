"""The sample labels reviewers can try with one click (samples/ in this repository).

Each sample is a made-up label with a known problem planted in it. Its application
data comes from samples/applications.csv, read with the same code that reads any
uploaded spreadsheet.
"""

import io
import json
import zipfile
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from app.intake.spreadsheet import ApplicationRow, read_spreadsheet

SAMPLES_DIR = Path(__file__).resolve().parent.parent / "samples"

# The samples shown as buttons, in this order. Titles come from the sample data.
FEATURED = [
    "old-tom-bourbon",
    "ridgewick-rye-wrong-abv",
    "copperfen-vodka-title-case-warning",
    "chateau-landrevin-wine",
    "vesperly-wine-specialty",
    "heronmere-gin-warning-wording--blurry",
    "granitefall-bourbon-prompt-injection",
]


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
            title=entry["title"],
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


ZIP_FOLDER = "ttb-sample-labels"


@cache
def sample_files_zip() -> bytes:
    """Every sample picture and the spreadsheet of their applications, as one ZIP file, so
    reviewers can try the upload forms with real files. Built in memory, once."""
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as archive:
        archive.write(
            SAMPLES_DIR / "applications.csv",
            f"{ZIP_FOLDER}/applications.csv",
            compress_type=zipfile.ZIP_DEFLATED,
        )
        # Pictures barely compress, so they are stored as they are.
        names = {name for label in sample_labels().values() for name in label.images}
        for name in sorted(names):
            archive.write(SAMPLES_DIR / "labels" / name, f"{ZIP_FOLDER}/labels/{name}")
    return out.getvalue()
