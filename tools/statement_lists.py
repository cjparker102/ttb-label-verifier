"""Do the reader's statement lists slow it down? An A/B on the same labels.

The reader as it is, against the same reader without the statement lists: the prompt's
paragraph about alcohol_statements and net_contents_statements, and those two fields of the
schema, taken out. Each label is read once by each, in random order, one request at a time,
and with no second request, so only the reader differs. Costs about 0.08 cents a request.
Only totals are published for the private real labels.

    uv run --env-file .env python -m tools.statement_lists --rows rows.jsonl samples cola-fourth:2
    uv run python -m tools.statement_lists --report rows.jsonl   # write the totals again
"""

import argparse
import asyncio
import base64
import json
import random
import statistics
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import anthropic
from pydantic import create_model

from app.config import Settings
from app.intake.images import shrink_to_jpeg, split_pages
from app.reading.prompt import INSTRUCTIONS
from app.reading.schema import LabelReading
from tools.evaluate import PRICE_IN, PRICE_OUT, load_entries, pictures_of
from tools.private_set import load_cases

OUT_DIR = Path(__file__).resolve().parent.parent / "docs" / "measurements"
LISTS = "- alcohol_statements and net_contents_statements:"
LIST_FIELDS = {"alcohol_statements", "net_contents_statements"}
WITH, WITHOUT = "with lists", "without lists"


def without_lists() -> tuple[str, type]:
    """The prompt and schema with the statement lists taken out, and nothing else changed."""
    prompt = INSTRUCTIONS[: INSTRUCTIONS.index(LISTS)].rstrip("\n") + "\n"
    fields = {
        name: (field.annotation, field)
        for name, field in LabelReading.model_fields.items()
        if name not in LIST_FIELDS
    }
    return prompt, create_model("LabelReading", **fields)


async def read(client, settings: Settings, images: list[bytes], prompt: str, schema) -> dict:
    content: list[dict] = []
    for number, image in enumerate(images, start=1):
        data = base64.standard_b64encode(image).decode("ascii")
        content.append({"type": "text", "text": f"Image {number}:"})
        content.append(
            {
                "type": "image",
                "source": {"type": "base64", "media_type": "image/jpeg", "data": data},
            }
        )
    content.append({"type": "text", "text": "Read this label."})
    start = time.perf_counter()
    response = await client.messages.parse(
        model=settings.model,
        max_tokens=8000,
        system=prompt,
        thinking={"type": "disabled"},
        output_config={"effort": settings.effort},
        messages=[{"role": "user", "content": content}],
        output_format=schema,
    )
    return {
        "seconds": round(time.perf_counter() - start, 3),
        "output_tokens": response.usage.output_tokens,
        "input_tokens": response.usage.input_tokens,
    }


def entries_of(name: str) -> list[dict]:
    if name == "samples":
        return load_entries(None)
    cases = load_cases(Path("private") / name / "cases.json")
    return [case for case in cases if case["kind"] == "as approved"]


async def measure(sets: list[tuple[str, int]], rows_path: Path) -> list[dict]:
    settings = Settings()
    client = anthropic.AsyncAnthropic(timeout=60, max_retries=0)
    variants = {WITH: (INSTRUCTIONS, LabelReading), WITHOUT: without_lists()}
    random.seed(20261020)
    rows = []
    with rows_path.open("w", encoding="utf-8") as out:
        for name, rounds in sets:
            for round_number in range(rounds):
                for entry in entries_of(name):
                    images = [
                        shrink_to_jpeg(data, settings.max_image_edge)
                        for file_name, picture in pictures_of(entry)
                        for _, data in split_pages(file_name, picture)
                    ]
                    order = list(variants)
                    random.shuffle(order)
                    for variant in order:
                        row = {"set": name, "round": round_number, "id": entry["id"]}
                        row |= {"variant": variant}
                        row |= await read(client, settings, images, *variants[variant])
                        rows.append(row)
                        out.write(json.dumps(row) + "\n")
                        out.flush()
    return rows


def percentile(values: list[float], share: float) -> float:
    ordered = sorted(values)
    return ordered[max(0, min(len(ordered) - 1, round(share * len(ordered)) - 1))]


def summary(rows: list[dict]) -> list[str]:
    """One table row a variant, then the paired differences, label by label."""
    lines = []
    for variant in (WITHOUT, WITH):
        mine = [row for row in rows if row["variant"] == variant]
        seconds = [row["seconds"] for row in mine]
        tokens = [row["output_tokens"] for row in mine]
        lines.append(
            f"| {variant} | {len(mine)} | {statistics.median(tokens):.0f} | "
            f"{statistics.median(seconds):.2f} s / {percentile(seconds, 0.95):.2f} s / "
            f"{max(seconds):.2f} s | {sum(s > 4 for s in seconds)} |"
        )
    pairs = defaultdict(dict)
    for row in rows:
        pairs[(row["set"], row["id"], row["round"])][row["variant"]] = row
    both = [pair for pair in pairs.values() if len(pair) == 2]
    more_tokens = [pair[WITH]["output_tokens"] - pair[WITHOUT]["output_tokens"] for pair in both]
    more_seconds = [pair[WITH]["seconds"] - pair[WITHOUT]["seconds"] for pair in both]
    lines.append(
        f"| Difference, label by label ({len(both)} pairs) | | "
        f"{statistics.median(more_tokens):+.0f} | "
        f"{statistics.median(more_seconds):+.2f} s median, {statistics.mean(more_seconds):+.2f} s "
        f"mean; slower with lists in {sum(d > 0 for d in more_seconds)} of {len(both)} | |"
    )
    return lines


def report(rows: list[dict]) -> str:
    header = [
        "| Reader | Requests | Output tokens (median) | Seconds (median / p95 / max) | Over 4 s |",
        "|---|---|---|---|---|",
    ]
    cost = sum(r["input_tokens"] * PRICE_IN + r["output_tokens"] * PRICE_OUT for r in rows) / 1e6
    lines = [
        f"# The reader with and without its statement lists, {datetime.now():%Y-%m-%d}",
        "",
        "The reader as it is, against the same reader with the statement lists (the prompt's "
        "paragraph and the schema's two fields) taken out. Each label read once by each, in "
        "random order, one request at a time, with no second request. Measured with "
        "`tools/statement_lists.py`, in process, from a home connection. Only totals are "
        f"published. AI cost: about ${cost:.2f}.",
        "",
    ]
    for name in sorted({row["set"] for row in rows}):
        mine = [row for row in rows if row["set"] == name]
        labels = len({row["id"] for row in mine})
        title = "The sample labels" if name == "samples" else f"Real labels, private set {name}"
        lines += [f"## {title} ({labels} labels)", "", *header, *summary(mine), ""]
    lines += [f"## All ({len(rows)} requests)", "", *header, *summary(rows)]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--rows", type=Path, help="where to keep each request's numbers")
    parser.add_argument("--report", type=Path, help="write the totals from saved rows only")
    parser.add_argument("sets", nargs="*", help="samples, or a private set, with :rounds")
    args = parser.parse_args()
    if args.report:
        rows = [json.loads(line) for line in args.report.read_text().splitlines()]
    else:
        sets = [(s.split(":")[0], int(s.split(":")[1]) if ":" in s else 1) for s in args.sets]
        rows = asyncio.run(measure(sets, args.rows))
    out = OUT_DIR / f"statement-lists-{datetime.now():%Y-%m-%d}.md"
    out.write_text(report(rows), encoding="utf-8")
    print(out.read_text())
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
