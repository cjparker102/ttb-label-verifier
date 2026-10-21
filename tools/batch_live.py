"""Times one large batch on a deployed app: the sample labels repeated to fill it.

The spreadsheet lists the samples over and over, up to --labels rows, and the ZIP holds
each sample picture once (rows may share pictures). With --picture-mb, each row gets its
own pictures instead, every file different, made to look like camera photos of about that
many MB a label, so the upload is as large as a real batch. Every row's results are scored against
the sample's expected results. Costs about 0.08 cents a label with Claude.

    uv run python -m tools.batch_live --url https://... --labels 300 --deployed-as "..."
    uv run python -m tools.batch_live --url https://... --labels 300 --picture-mb 0.9
"""

import argparse
import io
import time
import zipfile
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import httpx
from PIL import Image, ImageChops

from tools.evaluate import (
    ACCEPTABLE_ON_PHOTOS,
    LABELS_DIR,
    load_entries,
    results_from_excel,
    samples_zip,
    score,
    spreadsheet,
)

OUT_DIR = Path(__file__).resolve().parent.parent / "docs" / "measurements"


def tally(rows: list[dict], by_row: dict) -> tuple[Counter, Counter, int, Counter]:
    """Each row's results scored against its sample's expected results: field judgments,
    who read each label, rows with every field as expected, and the misses by sample."""
    judged, read_by, rows_as_expected, misses = Counter(), Counter(), 0, Counter()
    for number, entry in enumerate(rows, start=2):
        result = by_row[number]
        read_by[result["read_by"]] += 1
        judgments = score(entry, result["got"])["judgments"]
        judged.update(judgments.values())
        fine = {"exact", "note_difference"} | (
            ACCEPTABLE_ON_PHOTOS if entry.get("photo") else set()
        )
        rows_as_expected += all(j in fine for j in judgments.values())
        misses.update(
            f"{entry['id']}: {field} {j.replace('_', ' ')}"
            for field, j in judgments.items()
            if j not in fine
        )
    return judged, read_by, rows_as_expected, misses


GRAIN = 3  # the camera's grain: noise of this many gray levels, which JPEGs keep


def with_grain(picture: bytes) -> Image.Image:
    """A sample picture with fresh light grain, as a camera adds: every copy differs."""
    image = Image.open(io.BytesIO(picture)).convert("RGB")
    grain = Image.merge("RGB", [Image.effect_noise(image.size, GRAIN)] * 3)
    return ImageChops.add(image, grain, offset=-128)


def jpeg(image: Image.Image, quality: int) -> bytes:
    out = io.BytesIO()
    image.save(out, "JPEG", quality=quality)
    return out.getvalue()


def quality_for(image: Image.Image, target_bytes: int) -> int:
    """The highest JPEG quality that keeps the picture within `target_bytes`, or the lowest
    tried if none does."""
    low, high, best = 30, 95, 30
    while low <= high:
        quality = (low + high) // 2
        if len(jpeg(image, quality)) <= target_bytes:
            best, low = quality, quality + 1
        else:
            high = quality - 1
    return best


def own_pictures(rows: list[dict], megabytes: float) -> tuple[list[dict], bytes]:
    """Each row with its own pictures: its sample's, with fresh grain, saved as JPEGs of
    about `megabytes` a label in all, so no two files are alike. And the ZIP that holds them,
    stored as they are (JPEGs don't shrink further)."""
    qualities: dict[str, int] = {}
    with_own, out = [], io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_STORED) as archive:
        for number, entry in enumerate(rows, start=2):  # the spreadsheet row
            names = []
            for name in entry["images"]:
                image = with_grain((LABELS_DIR / name).read_bytes())
                if name not in qualities:
                    target = int(megabytes * 1e6 / len(entry["images"]))
                    qualities[name] = quality_for(image, target)
                names.append(f"row-{number:03d}-{Path(name).stem}.jpg")
                archive.writestr(names[-1], jpeg(image, qualities[name]))
            with_own.append({**entry, "images": names})
    return with_own, out.getvalue()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", required=True)
    parser.add_argument("--labels", type=int, default=300)
    parser.add_argument("--deployed-as", default="")
    parser.add_argument("--picture-mb", type=float, help="each row its own pictures, MB a label")
    args = parser.parse_args()
    samples = load_entries(None)
    rows = [samples[i % len(samples)] for i in range(args.labels)]
    url = args.url.rstrip("/")
    if args.picture_mb:
        rows, upload = own_pictures(rows, args.picture_mb)
        sent = (
            f"a ZIP of each row's own pictures, made to look like camera photos of about "
            f"{args.picture_mb:g} MB a label ({len(upload) / 1e6:.1f} MB)"
        )
    else:
        upload = samples_zip(samples)
        sent = f"a ZIP of the {len(samples)} labels' pictures ({len(upload) / 1e6:.1f} MB)"
    sheet = spreadsheet(rows)
    with httpx.Client(timeout=600) as client:
        client.get(url + "/")  # wake the app first, so its start-up isn't counted
        started_at = datetime.now(UTC)
        start = time.perf_counter()
        response = client.post(
            f"{url}/batches",
            files=[
                ("spreadsheet", ("applications.csv", sheet, "text/csv")),
                ("pictures", ("labels.zip", upload, "application/zip")),
            ],
            follow_redirects=False,
        )
        if response.status_code != 303:
            raise SystemExit(f"The batch upload failed: HTTP {response.status_code}")
        batch = url + response.headers["location"]
        uploaded = time.perf_counter() - start
        while client.get(f"{batch}/progress").json()["state"] != "finished":
            time.sleep(1)
        seconds = time.perf_counter() - start
        finished_at = datetime.now(UTC)
        page = client.get(batch).text
        by_row = results_from_excel(client.get(f"{batch}/results.xlsx").content)

    judged, read_by, rows_as_expected, misses = tally(rows, by_row)
    shown = next(
        (line.strip() for line in page.splitlines() if "seconds a label" in line), "not shown"
    )
    lines = [
        f"# A batch of {args.labels} labels on the live app, {datetime.now():%Y-%m-%d}",
        "",
        f"The {len(samples)} sample labels repeated to {args.labels} rows, uploaded as one "
        f"spreadsheet and {sent}, to {url}. App: {args.deployed_as or 'not stated'}. "
        "Measured with `tools/batch_live.py` from a home connection, from "
        f"{started_at:%H:%M:%S} to {finished_at:%H:%M:%S} UTC.",
        "",
        "| Measure | Result |",
        "|---|---|",
        f"| Upload size, spreadsheet and ZIP | {(len(sheet) + len(upload)) / 1e6:.1f} MB |",
        f"| Upload and unpacking, until the batch page opened | {uploaded:.1f} s |",
        f"| Whole batch, upload to finished | {seconds:.0f} s ({seconds / 60:.1f} minutes) |",
        f"| Per label | {seconds / args.labels:.2f} s |",
        f"| What the page says | {shown.replace('<p class="meta">', '').replace('</p>', '')} |",
        f"| Read by Claude / basic text reading | {read_by.get('AI reader', 0)} / "
        f"{read_by.get('Basic text reading', 0)} |",
        f"| Rows with every field as expected (Check this accepted on photo-like labels) | "
        f"{rows_as_expected} of {args.labels} |",
        f"| Field results | {', '.join(f'{k} {v}' for k, v in judged.most_common())} |",
    ]
    if misses:
        lines += ["", "Fields not as expected, by sample (count of rows):", ""]
        lines += [f"- {miss} ({n})" for miss, n in misses.most_common()]
    out = OUT_DIR / f"batch-{args.labels}-{datetime.now():%Y-%m-%d}.md"
    if out.exists():
        out = out.with_name(out.stem + f"-{datetime.now():%H%M}.md")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
