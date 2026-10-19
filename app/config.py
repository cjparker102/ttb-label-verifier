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


READERS = ("anthropic", "ocr")


@dataclass(frozen=True)
class Settings:
    reader: str = "anthropic"  # "ocr" uses only basic text reading
    ocr_fallback: bool = True  # use basic text reading when the AI reader fails
    model: str = "claude-haiku-5-5"
    thinking: bool = False  # picked from the Oct 19 timing test
    effort: str = "low"
    max_image_edge: int = 1568  # picked from the Oct 19 timing test
    max_images_per_label: int = 6
    max_image_bytes: int = 20 * MB
    max_request_bytes: int = 210 * MB  # a 200 MB batch upload plus the spreadsheet
    max_batch_files: int = 610  # pictures or ZIP files, plus the spreadsheet
    batch_concurrency: int = 8  # labels read at the same time within a batch
    batch_keep_seconds: int = 1800  # finished batch results are deleted after this
    checks_per_visitor: int = 30  # single-label checks per visitor, within the window below
    check_window_seconds: int = 600
    batches_per_visitor: int = 3
    batch_window_seconds: int = 3600
    labels_per_day: int = 2000  # for the whole app


def load_settings(env: Mapping[str, str] = os.environ) -> Settings:
    defaults = Settings()
    thinking = env.get("TTB_CLAUDE_THINKING", "off").strip().lower()
    if thinking not in ("off", "adaptive"):
        raise ValueError('TTB_CLAUDE_THINKING must be "off" or "adaptive"')
    effort = env.get("TTB_CLAUDE_EFFORT", defaults.effort).strip().lower()
    if effort not in EFFORTS:
        raise ValueError(f"TTB_CLAUDE_EFFORT must be one of {', '.join(EFFORTS)}")
    if thinking == "off" and effort not in EFFORTS_WITHOUT_THINKING:
        raise ValueError(
            f'TTB_CLAUDE_EFFORT "{effort}" needs thinking on. With TTB_CLAUDE_THINKING=off, '
            f"use {', '.join(EFFORTS_WITHOUT_THINKING)}."
        )
    reader = env.get("TTB_READER", defaults.reader).strip().lower()
    if reader not in READERS:
        raise ValueError(f"TTB_READER must be one of {', '.join(READERS)}")
    fallback = env.get("TTB_OCR_FALLBACK", "on").strip().lower()
    if fallback not in ("on", "off"):
        raise ValueError('TTB_OCR_FALLBACK must be "on" or "off"')
    return Settings(
        reader=reader,
        ocr_fallback=fallback == "on",
        model=env.get("TTB_CLAUDE_MODEL", defaults.model),
        thinking=thinking == "adaptive",
        effort=effort,
        max_image_edge=int(env.get("TTB_MAX_IMAGE_EDGE", defaults.max_image_edge)),
    )
