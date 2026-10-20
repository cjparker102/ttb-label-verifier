"""Times a single check when the AI provider can't be reached, as behind a firewall.

The app's real Anthropic client, with its timeouts, is pointed at an address that drops the
traffic (as a firewall does) and at one that refuses it. Each check goes through the same
deadline and second request as a single check in the app, then falls back to basic text
reading. No request reaches Anthropic, so it costs nothing.

    uv run python -m tools.blocked_provider
"""

import asyncio
import statistics
import time
from datetime import datetime
from pathlib import Path

import anthropic

from app.checking import check_one
from app.config import Settings
from app.reading.claude import ClaudeReader
from app.reading.providers import DeadlineReader, HedgedReader, client_options
from tools.evaluate import application_for, load_entries, pictures_of

OUT_DIR = Path(__file__).resolve().parent.parent / "docs" / "measurements"
BLOCKED = {
    "dropped (no answer, as a firewall that drops traffic)": "https://10.255.255.1",
    "refused (the connection is turned away at once)": "http://127.0.0.1:9",
}
RUNS = 3


async def one_check(base_url: str, settings: Settings) -> tuple[float, str]:
    client = anthropic.AsyncAnthropic(
        api_key="not-a-key", base_url=base_url, **client_options(settings)
    )
    reader = DeadlineReader(
        HedgedReader(
            ClaudeReader(
                client, thinking=settings.thinking, effort=settings.effort, model=settings.model
            ),
            settings.hedge_after_seconds,
        ),
        settings.reading_deadline_seconds,
    )
    entry = load_entries(["old-tom-bourbon"])[0]
    start = time.perf_counter()
    outcome = await check_one(
        application_for(entry), pictures_of(entry), reader, settings.max_image_edge, outline=True
    )
    return time.perf_counter() - start, outcome.read_by


def main() -> None:
    settings = Settings()
    lines = [
        f"# A blocked AI provider, {datetime.now():%Y-%m-%d}",
        "",
        "A single check of the sample `old-tom-bourbon`, in process on a laptop, with the app's "
        "client pointed at an address that can't be reached. Connect timeout "
        f"{settings.connect_seconds:g} s, reading deadline "
        f"{settings.reading_deadline_seconds:g} s, one retry, a second request after "
        f"{settings.hedge_after_seconds:g} s. Measured with `tools/blocked_provider.py`.",
        "",
        "| Provider address | Read by | Check time, each run | Median |",
        "|---|---|---|---|",
    ]
    for kind, url in BLOCKED.items():
        runs = [asyncio.run(one_check(url, settings)) for _ in range(RUNS)]
        seconds = [s for s, _ in runs]
        read_by = ", ".join(sorted({r for _, r in runs}))
        shown = ", ".join(f"{s:.1f} s" for s in seconds)
        lines.append(f"| {kind} | {read_by} | {shown} | {statistics.median(seconds):.1f} s |")
        print(lines[-1])
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"blocked-provider-{datetime.now():%Y-%m-%d}.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
