"""Checks on the style sheet that a page test can't see.

Contrast is measured with the WCAG 2 formula. Text aims for AAA (7:1), the plan's
goal for agents reading small print all day. Borders that show where a control is
need 3:1 (WCAG 1.4.11).
"""

import re
from pathlib import Path

import pytest

CSS = (Path(__file__).resolve().parents[2] / "app" / "static" / "style.css").read_text()
TOKENS = dict(re.findall(r"--([\w-]+):\s*(#[0-9a-fA-F]{3,6});", CSS.split("}", 1)[0]))


def color(value: str) -> str:
    """A hex color, from a token name ("text") or a hex value."""
    return TOKENS[value] if not value.startswith("#") else value


def luminance(hex_color: str) -> float:
    digits = hex_color.lstrip("#")
    if len(digits) == 3:
        digits = "".join(c * 2 for c in digits)
    channels = [int(digits[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(foreground: str, background: str) -> float:
    lighter, darker = sorted(
        (luminance(color(foreground)), luminance(color(background))), reverse=True
    )
    return (lighter + 0.05) / (darker + 0.05)


def rule(selector: str) -> str:
    """The declarations of one rule in the style sheet."""
    match = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", CSS)
    assert match, f"no rule for {selector}"
    return match.group(1)


def background_of(selector: str) -> str:
    """The rule's background, as a hex color or a token name."""
    value = re.search(r"background:\s*(#[0-9a-fA-F]{3,6}|var\(--[\w-]+\))", rule(selector)).group(1)
    return value.removeprefix("var(--").removesuffix(")")


TEXT = [
    ("text", "page"),
    ("text", "panel"),
    ("muted", "page"),
    ("muted", "panel"),
    ("#fff", "brand"),
    ("brand", "page"),
    ("pass", "pass-bg"),
    ("review", "review-bg"),
    ("fail", "fail-bg"),
    ("not-needed", "not-needed-bg"),
    ("pass", "page"),
    ("review", "page"),
    ("fail", "page"),
]


@pytest.mark.parametrize(("foreground", "background"), TEXT)
def test_text_colors_meet_aaa(foreground, background):
    assert contrast(foreground, background) >= 7


@pytest.mark.parametrize(
    ("foreground", "selector"),
    [
        ("#fff", ".button-primary:hover"),
        ("#fff", ".jump-link"),
        ("#fff", ".jump-link:hover"),
        ("#fff", ".button-primary[disabled]"),
        ("brand", ".button-secondary:hover"),
        ("text", ".drop-zone"),
        ("text", ".drop-zone.dragging"),
    ],
)
def test_buttons_and_drop_zones_meet_aaa_in_every_state(foreground, selector):
    assert contrast(foreground, background_of(selector)) >= 7


def test_control_borders_stand_out_from_the_page():
    assert contrast("line", "page") >= 3


def test_focus_ring_has_a_dark_edge_as_well_as_a_light_one():
    focus = rule(":focus-visible")
    assert "var(--focus)" in focus and "var(--text)" in focus
    assert contrast("text", "focus") >= 7  # the dark edge against the yellow ring


def test_tokens_were_found():
    assert {"text", "page", "brand", "pass", "review", "fail"} <= TOKENS.keys()


def test_form_boxes_can_shrink_to_a_narrow_screen():
    # A fieldset is never narrower than its contents unless told otherwise, so a file
    # input's "No file chosen" pushed the form off a 320-pixel screen (400% zoom).
    assert "min-width: 0" in rule("fieldset")
