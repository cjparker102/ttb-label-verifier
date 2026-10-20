"""Settings, read only from environment variables (see .env.example).

The app's own variables start with TTB_, so they can't clash with variables
other tools set (Claude Code, for one, sets CLAUDE_EFFORT in its shells).
"""

import os
from collections.abc import Mapping
from dataclasses import dataclass

MB = 1024 * 1024
EFFORTS = ("low", "medium", "high", "xhigh", "max")
# Claude Haiku 5.5 accepts thinking turned off only at these effort levels.
EFFORTS_WITHOUT_THINKING = ("low", "medium", "high")
READERS = ("anthropic", "foundry", "ocr")


@dataclass(frozen=True)
class Settings:
    reader: str = "anthropic"  # "foundry" uses Claude in Azure; "ocr" basic text reading only
    ocr_fallback: bool = True  # use basic text reading when the AI reader fails
    model: str = "claude-haiku-5-5"  # with Foundry, the deployment name
    thinking: bool = False  # picked from the Oct 19 timing test
    effort: str = "low"
    foundry_resource: str = ""  # the Foundry resource name, for TTB_READER=foundry
    labels_per_minute: int = 0  # pace calls to the AI reader; 0 means no pacing
    max_image_edge: int = 1568  # picked from the Oct 19 timing test
    max_images_per_label: int = 6
    max_image_bytes: int = 20 * MB
    max_request_bytes: int = 210 * MB  # a 200 MB batch upload plus the spreadsheet
    max_batch_files: int = 610  # pictures or ZIP files, plus the spreadsheet
    batch_concurrency: int = 8  # labels read at the same time within a batch
    # A single check asks the AI reader again if it hasn't answered by then. Batches
    # don't: their labels are read eight at a time, and nobody waits on one of them.
    hedge_after_seconds: float = 4.0
    # When the AI provider can't be reached, as behind a firewall that drops the traffic,
    # a check falls back to basic text reading quickly: a connection must open within this
    # many seconds, and a label's whole reading must finish within the deadline.
    connect_seconds: float = 3.0
    reading_deadline_seconds: float = 8.0
    batch_keep_seconds: int = 1800  # finished batch results are deleted after this
    # Pictures of batch labels not yet checked, in all, are held in memory. Above this a
    # new batch is turned away until there is room, so queued uploads can't use up the
    # replica's 2 GiB.
    max_waiting_bytes: int = 600 * MB
    # Per visitor, within the windows below. A visitor is an address, and a whole office
    # may share one, so these are generous; the daily limit and the spend limit on the
    # Anthropic workspace are the real protection.
    checks_per_visitor: int = 300  # single-label checks
    check_window_seconds: int = 600
    batches_per_visitor: int = 30
    batch_window_seconds: int = 3600
    labels_per_day: int = 2000  # for the whole app


def whole_number(env: Mapping[str, str], name: str, default: int, minimum: int) -> int:
    text = env.get(name, str(default)).strip()
    if not text.isdigit() or int(text) < minimum:
        raise ValueError(f"{name} must be a whole number of at least {minimum}")
    return int(text)


def load_settings(env: Mapping[str, str] = os.environ) -> Settings:
    defaults = Settings()
    reader = env.get("TTB_READER", defaults.reader).strip().lower()
    if reader not in READERS:
        raise ValueError(f"TTB_READER must be one of {', '.join(READERS)}")

    # Claude in Foundry gives structured answers only with thinking on, so it defaults on.
    thinking = env.get("TTB_CLAUDE_THINKING", "adaptive" if reader == "foundry" else "off")
    thinking = thinking.strip().lower()
    if thinking not in ("off", "adaptive"):
        raise ValueError('TTB_CLAUDE_THINKING must be "off" or "adaptive"')
    if reader == "foundry" and thinking == "off":
        raise ValueError("Claude in Foundry needs TTB_CLAUDE_THINKING=adaptive")
    effort = env.get("TTB_CLAUDE_EFFORT", defaults.effort).strip().lower()
    if effort not in EFFORTS:
        raise ValueError(f"TTB_CLAUDE_EFFORT must be one of {', '.join(EFFORTS)}")
    if thinking == "off" and effort not in EFFORTS_WITHOUT_THINKING:
        raise ValueError(
            f'TTB_CLAUDE_EFFORT "{effort}" needs thinking on. With TTB_CLAUDE_THINKING=off, '
            f"use {', '.join(EFFORTS_WITHOUT_THINKING)}."
        )

    foundry_resource = env.get("TTB_FOUNDRY_RESOURCE", "").strip()
    if reader == "foundry" and not foundry_resource:
        raise ValueError("TTB_READER=foundry needs TTB_FOUNDRY_RESOURCE, the Foundry resource name")
    fallback = env.get("TTB_OCR_FALLBACK", "on").strip().lower()
    if fallback not in ("on", "off"):
        raise ValueError('TTB_OCR_FALLBACK must be "on" or "off"')

    return Settings(
        reader=reader,
        ocr_fallback=fallback == "on",
        model=env.get("TTB_CLAUDE_MODEL", defaults.model),
        thinking=thinking == "adaptive",
        effort=effort,
        foundry_resource=foundry_resource,
        labels_per_minute=whole_number(env, "TTB_LABELS_PER_MINUTE", 0, 0),
        max_image_edge=whole_number(env, "TTB_MAX_IMAGE_EDGE", defaults.max_image_edge, 200),
        batch_concurrency=whole_number(env, "TTB_BATCH_CONCURRENCY", defaults.batch_concurrency, 1),
    )
