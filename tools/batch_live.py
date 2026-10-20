"""Times one large batch on a deployed app: the sample labels repeated to fill it.

The spreadsheet lists the 31 samples over and over, up to --labels rows, and the ZIP holds
each sample picture once (rows may share pictures). Every row's results are scored against
the sample's expected results. Costs about 0.08 cents a label with Claude.

    uv run python -m tools.batch_live --url https://... --labels 300 --deployed-as "..."
"""

import argparse
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

import httpx

from tools.evaluate import (
    ACCEPTABLE_ON_PHOTOS,
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", required=True)
    parser.add_argument("--labels", type=int, default=300)
    parser.add_argument("--deployed-as", default="")
    args = parser.parse_args()
    samples = load_entries(None)
    rows = [samples[i % len(samples)] for i in range(args.labels)]
    url = args.url.rstrip("/")
    upload = samples_zip(samples)
    with httpx.Client(timeout=300) as client:
        client.get(url + "/")  # wake the app first, so its start-up isn't counted
        start = time.perf_counter()
        response = client.post(
            f"{url}/batches",
            files=[
                ("spreadsheet", ("applications.csv", spreadsheet(rows), "text/csv")),
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
        f"spreadsheet and a ZIP of the {len(samples)} labels' pictures "
        f"({len(upload) / 1e6:.1f} MB), "
        f"to {url}. App: {args.deployed_as or 'not stated'}. Measured with `tools/batch_live.py` "
        "from a home connection.",
        "",
        "| Measure | Result |",
        "|---|---|",
        f"| Upload, until the batch page opened | {uploaded:.1f} s |",
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
