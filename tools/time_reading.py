"""Times one sample label at two image sizes, with thinking off and on.

Run from the project root. The API key is loaded from .env and never printed:
    uv run --env-file .env python -m tools.time_reading

By default this makes 12 real API calls (2 sizes x 2 thinking modes x 3 runs),
costing about one cent. It prints a summary and saves every timing and reading
to docs/measurements/ so the reported numbers can be checked.
"""

import argparse
import asyncio
import json
import statistics
import time
from datetime import datetime
from pathlib import Path

import anthropic

from app.intake.images import shrink_to_jpeg
from app.reading.claude import MODEL, ClaudeReader, ReadingFailed
from app.reading.schema import LabelReading
from tools.make_samples import FIELDS, LABELS_DIR, SAMPLES_DIR

OUT_DIR = Path(__file__).resolve().parent.parent / "docs" / "measurements"
SIZES = (2576, 1568)
THINKING = {False: "off", True: "adaptive"}
EFFORT = "low"
# Claude Haiku 5.5, USD per million tokens, for prompts up to 100K tokens.
PRICE_IN, PRICE_OUT = 0.10, 0.50


def load_sample(sample_id: str) -> dict:
    entries = json.loads((SAMPLES_DIR / "expected.json").read_text(encoding="utf-8"))
    for entry in entries:
        if entry["id"] == sample_id:
            return entry
    raise SystemExit(f"No sample named {sample_id}")


def compare(reading: LabelReading, truth: dict) -> dict[str, list[str]]:
    """List what the reading got wrong, field by field. Empty means all exact."""
    problems = {}
    for name in FIELDS:
        got, want = getattr(reading, name), truth[name]
        issues = []
        if got.text != want["text"]:
            issues.append(f"text {got.text!r}, expected {want['text']!r}")
        if got.image_number != want["image_number"]:
            issues.append(f"image {got.image_number}, expected {want['image_number']}")
        expected_readability = "clear" if want["text"] is not None else "not_found"
        if got.readability != expected_readability:
            issues.append(f"readability {got.readability}, expected {expected_readability}")
        if name == "government_warning" and want["text"] is not None:
            expected_bold = "yes" if want["heading_bold"] else "no"
            if got.heading_bold != expected_bold:
                issues.append(f"heading_bold {got.heading_bold}, expected {expected_bold}")
            if got.rest_bold != "no":
                issues.append(f"rest_bold {got.rest_bold}, expected no")
        if issues:
            problems[name] = issues
    return problems


async def run(sample_id: str, runs: int) -> dict:
    entry = load_sample(sample_id)
    originals = [(LABELS_DIR / name).read_bytes() for name in entry["images"]]

    prepared = {}
    for size in SIZES:
        start = time.perf_counter()
        images = [shrink_to_jpeg(data, size) for data in originals]
        prepared[size] = {
            "images": images,
            "shrink_seconds": round(time.perf_counter() - start, 3),
            "jpeg_bytes": [len(image) for image in images],
        }

    client = anthropic.AsyncAnthropic(max_retries=0, timeout=60)
    try:
        await client.models.list(limit=1)  # open the connection so run 1 is timed fairly
    except anthropic.APIError as error:
        print(f"Warm-up call failed ({error}); continuing.")

    records = []
    for number in range(1, runs + 1):
        for size in SIZES:
            for thinking, thinking_name in THINKING.items():
                record = {"run": number, "max_edge": size, "thinking": thinking_name}
                reader = ClaudeReader(client, thinking=thinking, effort=EFFORT)
                try:
                    result = await reader.read(prepared[size]["images"])
                except (anthropic.APIError, ReadingFailed) as error:
                    record["error"] = f"{type(error).__name__}: {error}"
                    print(f"run {number}  {size} px  thinking {thinking_name:8}  ERROR {error}")
                else:
                    problems = compare(result.reading, entry["truth"])
                    record.update(
                        seconds=round(result.seconds, 2),
                        input_tokens=result.input_tokens,
                        output_tokens=result.output_tokens,
                        problems=problems,
                        reading=result.reading.model_dump(mode="json"),
                    )
                    print(
                        f"run {number}  {size} px  thinking {thinking_name:8}  "
                        f"{result.seconds:5.2f} s  {7 - len(problems)}/7 fields exact"
                    )
                records.append(record)

    return {
        "measured_at": datetime.now().isoformat(timespec="seconds"),
        "model": MODEL,
        "effort": EFFORT,
        "sample": sample_id,
        "images": entry["images"],
        "prepared": {
            size: {"shrink_seconds": info["shrink_seconds"], "jpeg_bytes": info["jpeg_bytes"]}
            for size, info in prepared.items()
        },
        "runs": records,
    }


def summarize(results: dict) -> str:
    lines = [
        "| Max edge | Thinking | Median s | Min s | Max s | Input tokens | Output tokens "
        "| All 7 fields exact | Cost per label |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for size in SIZES:
        for thinking_name in THINKING.values():
            group = [
                r
                for r in results["runs"]
                if r["max_edge"] == size and r["thinking"] == thinking_name and "error" not in r
            ]
            failed = sum(
                1
                for r in results["runs"]
                if r["max_edge"] == size and r["thinking"] == thinking_name and "error" in r
            )
            if not group:
                lines.append(f"| {size} | {thinking_name} | all {failed} runs failed |||||||")
                continue
            seconds = [r["seconds"] for r in group]
            tokens_in = statistics.mean(r["input_tokens"] for r in group)
            tokens_out = statistics.mean(r["output_tokens"] for r in group)
            exact = sum(1 for r in group if not r["problems"])
            cost = (tokens_in * PRICE_IN + tokens_out * PRICE_OUT) / 1_000_000
            note = f" ({failed} failed)" if failed else ""
            lines.append(
                f"| {size} | {thinking_name} | {statistics.median(seconds):.2f} | "
                f"{min(seconds):.2f} | {max(seconds):.2f} | {tokens_in:,.0f} | "
                f"{tokens_out:,.0f} | {exact}/{len(group)}{note} | ${cost:.4f} |"
            )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sample", default="old-tom-bourbon")
    parser.add_argument("--runs", type=int, default=3)
    args = parser.parse_args()

    results = asyncio.run(run(args.sample, args.runs))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"timing-{results['measured_at'][:10]}-{args.sample}.json"
    path.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print()
    print(summarize(results))
    for record in results["runs"]:
        for name, issues in record.get("problems", {}).items():
            print(f"run {record['run']} {record['max_edge']} px {record['thinking']}: {name}: ")
            for issue in issues:
                print(f"    {issue}")
    print(f"\nSaved: {path}")


if __name__ == "__main__":
    main()
