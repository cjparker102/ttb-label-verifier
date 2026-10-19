"""Times single checks on a deployed app, end to end, with a sample label as drawn or
blown up to the size of a phone photo.

Run from the project root:
    uv run python -m tools.time_live --url https://... --sample tallgrass-bourbon-two-sides --phone

Each run is one real check, which costs about 0.07 cents with Claude. For each run it
prints the time end to end from this computer, and the time inside the app: the page's
"Checked in" time, which includes the wait for outlines. Nothing is saved; the numbers
are copied into a measurement note in docs/measurements/.
"""

import argparse
import io
import statistics

from PIL import Image

from tools.evaluate import check_form, from_page, load_entries, post_check
from tools.make_samples import LABELS_DIR

PHONE_WIDTH = 4032  # a 12-megapixel phone photo is 4032 x 3024


def phone_photo(data: bytes) -> bytes:
    """A sample picture blown up to a phone photo's width, with camera-like grain so the
    JPEG is as large as a real one (several MB; a smooth drawing would compress to 1 MB)."""
    picture = Image.open(io.BytesIO(data)).convert("RGB")
    height = round(PHONE_WIDTH * picture.height / picture.width)
    picture = picture.resize((PHONE_WIDTH, height), Image.Resampling.LANCZOS)
    grain = Image.effect_noise(picture.size, 40).convert("RGB")
    out = io.BytesIO()
    Image.blend(picture, grain, 0.12).save(out, format="JPEG", quality=92)
    return out.getvalue()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", required=True)
    parser.add_argument("--sample", default="ridgewick-rye-wrong-abv")
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--phone", action="store_true", help="send phone-sized JPEGs")
    args = parser.parse_args()

    import httpx

    [entry] = load_entries([args.sample])
    files = []
    for name in entry["images"]:
        data = (LABELS_DIR / name).read_bytes()
        if args.phone:
            name, data = name.rsplit(".", 1)[0] + ".jpg", phone_photo(data)
        files.append(("images", (name, data)))
    size = sum(len(data) for _, (_, data) in files)
    print(f"{args.sample}: {len(files)} picture(s), {size / 1e6:.2f} MB")

    ends, insides = [], []
    with httpx.Client(timeout=120) as client:
        for run in range(1, args.runs + 1):
            response, seconds = post_check(client, args.url.rstrip("/"), check_form(entry), files)
            shown = from_page(response.text)
            ends.append(seconds)
            insides.append(shown["server_seconds"])
            print(
                f"run {run}: HTTP {response.status_code}, end to end {seconds:.2f} s, inside the "
                f"app {shown['server_seconds']} s, read by {shown['read_by']}, outlined "
                f"{len(shown['outlined'])} of {len(shown['flagged_on_label'])} fields to look at"
            )
    print(
        f"median: end to end {statistics.median(ends):.2f} s, "
        f"inside the app {statistics.median(insides):.2f} s"
    )


if __name__ == "__main__":
    main()
