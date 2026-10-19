"""Advice for taking a better photo of a label. Tips never change any result."""

from io import BytesIO

from PIL import Image

LOW_RESOLUTION_EDGE = 1000  # pictures smaller than this on their longer side

# In the order shown. Keys match the problems the AI reader reports, plus
# "low_resolution", which code finds on its own.
TIPS = {
    "glare": "Glare covers part of the label. Turn off the flash, or tilt the bottle so light "
    "doesn't reflect straight back at the camera.",
    "blur": "The picture is blurry. Hold the camera still, and tap the label on the screen to "
    "focus before taking the photo.",
    "angle": "The label was photographed at an angle. Hold the camera straight in front of the "
    "label.",
    "dark": "The picture is dark. Use more light, such as a window or a desk lamp.",
    "too_small": "The label is small in the picture. Move closer, so the label fills most of "
    "the frame.",
    "cut_off": "Part of the label is cut off. Step back a little, so the whole label is in the "
    "picture.",
    "low_resolution": f"The picture is small (under {LOW_RESOLUTION_EDGE:,} pixels across). "
    "Use a larger picture, or a camera's full-size photo.",
}


def low_resolution(pictures: list[bytes]) -> bool:
    """True if any picture is smaller than LOW_RESOLUTION_EDGE on its longer side."""
    for picture in pictures:
        with Image.open(BytesIO(picture)) as image:
            if max(image.size) < LOW_RESOLUTION_EDGE:
                return True
    return False


def photo_tips(problems: list[str]) -> list[str]:
    """One tip per known problem, in a fixed order, without repeats."""
    found = set(problems)
    return [tip for key, tip in TIPS.items() if key in found]
