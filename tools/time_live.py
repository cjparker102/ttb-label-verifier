"""Times single checks on a deployed app, end to end, with a sample label as drawn or
blown up to the size of a phone photo.

Run from the project root:
    uv run python -m tools.time_live --url https://... --sample tallgrass-bourbon-two-sides --phone
    uv run python -m tools.time_live --url https://... --sample all --runs 2

Each check costs about 0.07 cents with Claude. A run checks the sample once, or with
"--sample all", every sample once, in turn. For each check it prints the time end to end
from this computer, and the time inside the app: the page's "Checked in" time, which
includes the wait for outlines. Nothing is saved; the numbers are copied into a
measurement note in docs/measurements/.
"""

import argparse
import io
import statistics

from PIL import Image

from tools.evaluate import check_form, from_page, load_entries, percentile, post_check
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


def summary(times: list[float]) -> str:
    return (
        f"median {statistics.median(times):.2f} s, p95 {percentile(times, 0.95):.2f} s, "
        f"slowest {max(times):.2f} s"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", required=True)
    parser.add_argument(
        "--sample", default="ridgewick-rye-wrong-abv", help='a sample id, or "all" for every one'
    )
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--phone", action="store_true", help="send phone-sized JPEGs")
    args = parser.parse_args()

    import httpx

    uploads = []
    for entry in load_entries(None if args.sample == "all" else [args.sample]):
        files = []
        for name in entry["images"]:
            data = (LABELS_DIR / name).read_bytes()
            if args.phone:
                name, data = name.rsplit(".", 1)[0] + ".jpg", phone_photo(data)
            files.append(("images", (name, data)))
        size = sum(len(data) for _, (_, data) in files)
        print(f"{entry['id']}: {len(files)} picture(s), {size / 1e6:.2f} MB")
        uploads.append((entry, files))

    ends, insides = [], []
    with httpx.Client(timeout=120) as client:
        for run in range(1, args.runs + 1):
            for entry, files in uploads:
                response, seconds = post_check(
                    client, args.url.rstrip("/"), check_form(entry), files
                )
                shown = from_page(response.text)
                ends.append(seconds)
                insides.append(shown["server_seconds"])
                print(
                    f"run {run}, {entry['id']}: HTTP {response.status_code}, end to end "
                    f"{seconds:.2f} s, inside the app {shown['server_seconds']} s, read by "
                    f"{shown['read_by']}, outlined {len(shown['outlined'])} of "
                    f"{len(shown['flagged_on_label'])} fields to look at"
                )
    under = sum(1 for seconds in ends if seconds < 5)
    print(f"{len(ends)} checks, {under} under 5 seconds end to end")
    print(f"end to end: {summary(ends)}")
    print(f"inside the app: {summary(insides)}")


if __name__ == "__main__":
    main()
