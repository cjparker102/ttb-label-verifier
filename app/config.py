"""Settings, read only from environment variables (see .env.example)."""

import os
from collections.abc import Mapping
from dataclasses import dataclass

MB = 1024 * 1024


@dataclass(frozen=True)
class Settings:
    model: str = "claude-haiku-5-5"
    thinking: bool = False  # picked from the Oct 19 timing test
    effort: str = "low"
    max_image_edge: int = 1568  # picked from the Oct 19 timing test
    max_images_per_label: int = 6
    max_image_bytes: int = 20 * MB
    max_request_bytes: int = 125 * MB  # 6 images of 20 MB plus form fields


def load_settings(env: Mapping[str, str] = os.environ) -> Settings:
    defaults = Settings()
    thinking = env.get("CLAUDE_THINKING", "off").strip().lower()
    if thinking not in ("off", "adaptive"):
        raise ValueError('CLAUDE_THINKING must be "off" or "adaptive"')
    return Settings(
        model=env.get("CLAUDE_MODEL", defaults.model),
        thinking=thinking == "adaptive",
        effort=env.get("CLAUDE_EFFORT", defaults.effort),
        max_image_edge=int(env.get("MAX_IMAGE_EDGE", defaults.max_image_edge)),
    )
