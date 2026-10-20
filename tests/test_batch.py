import asyncio
import json

import pytest

from app.batch import SECONDS_PER_LABEL, BatchStore, ItemState, new_job, picture_sizes, run_job
from app.intake.matching import MatchedRow
from app.intake.spreadsheet import ApplicationRow
from app.reading.ocr import tesseract_available
from app.rules.application import Application, BeverageType
from app.rules.results import Status
from app.rules.warning import GOVERNMENT_WARNING
from tests.stand_ins import FailingReader, ReplayReader, perfect_reading, recorded_reading
from tools.evaluate import application_for
from tools.make_samples import LABELS_DIR, SAMPLES_DIR

EXPECTED = json.loads((SAMPLES_DIR / "expected.json").read_text(encoding="utf-8"))

OLD_TOM = Application(
    BeverageType.DISTILLED_SPIRITS,
    "OLD TOM DISTILLERY",
    "Kentucky Straight Bourbon Whiskey",
    "45% Alc./Vol. (90 Proof)",
    "750 mL",
    "Old Tom Distillery, Bardstown, Kentucky",
)
FRONT = LABELS_DIR / "old-tom-bourbon_front.png"


def _tiny_png() -> bytes:
    from io import BytesIO

    from PIL import Image

    out = BytesIO()
    Image.new("RGB", (40, 40), "white").save(out, format="PNG")
    return out.getvalue()


TINY_PNG = _tiny_png()


def good_row(number, application=OLD_TOM):
    row = ApplicationRow(number, ("front.png",), application, (), application.brand_name)
    return MatchedRow(row, (("front.png", FRONT.read_bytes()),), ())


def run(job, reader=None, concurrency=4, gate=None):
    async def go():
        await run_job(
            job, reader or ReplayReader(), 1568, concurrency, gate or asyncio.Semaphore(1)
        )

    asyncio.run(go())


def test_rows_that_cannot_be_checked_say_why():
    problem_row = MatchedRow(
        ApplicationRow(3, ("x.png",), None, ("The brand name is blank.",), ""), (), ()
    )
    missing_row = MatchedRow(
        ApplicationRow(4, ("gone.png",), OLD_TOM, (), "OLD TOM DISTILLERY"), (), ("gone.png",)
    )
    job = new_job([good_row(2), problem_row, missing_row], [], [])
    assert [item.state for item in job.items] == [
        ItemState.WAITING,
        ItemState.NOT_CHECKED,
        ItemState.NOT_CHECKED,
    ]
    assert job.items[1].problem == "The brand name is blank."
    assert job.items[2].problem == "These pictures were not in the upload: gone.png."
    assert len(job.work) == 1
    assert (job.done, job.total) == (2, 3)


def test_job_ids_are_long_and_unique():
    ids = {new_job([], [], []).id for _ in range(100)}
    assert len(ids) == 100
    assert all(len(job_id) >= 20 for job_id in ids)


def test_running_a_job_checks_every_label_and_lets_go_of_pictures():
    job = new_job([good_row(2), good_row(3)], [], [])
    work = list(job.work)
    run(job)
    assert job.state == "finished"
    assert (job.done, job.total) == (2, 2)
    for item in job.items:
        assert item.state == ItemState.DONE
        assert item.outcome.result.status == Status.PASS
        assert item.outcome.images == []  # full-size pictures dropped
        assert [p[:2] for p in item.previews] == [b"\xff\xd8"]  # a JPEG of each picture
    assert all(w.pictures == [] for w in work)
    assert job.work == []


def test_reader_failure_falls_back_to_basic_text_reading():
    job = new_job([good_row(2)], [], [])
    run(job, reader=FailingReader())
    assert job.items[0].state == ItemState.DONE
    assert job.items[0].outcome.read_by == "ocr"


def test_reader_failure_without_fallback_marks_only_that_label():
    job = new_job([good_row(2)], [], [])

    async def go():
        await run_job(job, FailingReader(), 1568, 4, asyncio.Semaphore(1), ocr_fallback=False)

    asyncio.run(go())
    assert job.items[0].state == ItemState.NOT_CHECKED
    assert "could not read this label" in job.items[0].problem
    assert job.state == "finished"


def test_a_picture_that_is_not_an_image():
    row = ApplicationRow(2, ("front.png",), OLD_TOM, (), "OLD TOM DISTILLERY")
    job = new_job([MatchedRow(row, (("front.png", b"not a picture"),), ())], [], [])
    run(job)
    assert job.items[0].state == ItemState.NOT_CHECKED
    assert "not an image" in job.items[0].problem


def test_no_more_than_the_allowed_number_of_labels_are_read_at_once():
    class SlowReader(ReplayReader):
        def __init__(self):
            super().__init__()
            self.now = self.most = 0

        async def read(self, images):
            self.now += 1
            self.most = max(self.most, self.now)
            await asyncio.sleep(0.2)  # long enough to overlap, even on a slow machine
            self.now -= 1
            return await super().read(images)

    def tiny_row(number):  # tiny pictures, so preparing them never delays the reads
        row = ApplicationRow(number, ("tiny.png",), OLD_TOM, (), OLD_TOM.brand_name)
        return MatchedRow(row, (("tiny.png", TINY_PNG),), ())

    reader = SlowReader()
    job = new_job([tiny_row(n) for n in range(2, 12)], [], [])
    run(job, reader=reader, concurrency=3)
    assert reader.most <= 3  # the limit
    assert reader.most == 3  # and labels really were read side by side


def test_a_second_batch_waits_for_the_first():
    async def go():
        release = asyncio.Event()

        class HeldReader(ReplayReader):
            async def read(self, images):
                await release.wait()
                return await super().read(images)

        gate = asyncio.Semaphore(1)
        first, second = new_job([good_row(2)], [], []), new_job([good_row(2)], [], [])
        tasks = [
            asyncio.create_task(run_job(first, HeldReader(), 1568, 4, gate)),
            asyncio.create_task(run_job(second, HeldReader(), 1568, 4, gate)),
        ]
        await asyncio.sleep(0.05)
        states = (first.state, second.state)
        release.set()
        await asyncio.gather(*tasks)
        return states

    assert asyncio.run(go()) == ("running", "queued")


def test_finished_jobs_are_forgotten_after_a_while():
    now = [0.0]
    store = BatchStore(keep_seconds=1800, clock=lambda: now[0])
    finished, running = new_job([], [], []), new_job([], [], [])
    finished.state, finished.finished_at = "finished", 0.0
    running.state = "running"
    store.add(finished)
    store.add(running)
    now[0] = 1801
    assert store.get(finished.id) is None
    assert store.get(running.id) is running


def test_a_batch_that_crashes_still_finishes(monkeypatch):
    # Reader failures fall back to basic text reading, so make the checking itself break.
    async def broken_check(*args, **kwargs):
        raise RuntimeError("unexpected")

    monkeypatch.setattr("app.batch.check_one", broken_check)
    job = new_job([good_row(2), good_row(3)], [], [])
    run(job)
    assert job.state == "finished"
    assert all(item.state == ItemState.NOT_CHECKED for item in job.items)
    assert "Something went wrong" in job.items[0].problem


def row_holding(number, data):
    row = ApplicationRow(number, ("front.png",), OLD_TOM, (), OLD_TOM.brand_name)
    return MatchedRow(row, (("front.png", data),), ())


def test_a_picture_two_labels_share_is_counted_once():
    shared = bytes(100)
    rows = [row_holding(2, shared), row_holding(3, shared), row_holding(4, bytes(50))]
    assert picture_sizes(new_job(rows, [], []).work) == [100, 0, 50]


def test_a_new_batch_waits_until_labels_ahead_of_it_make_room():
    store = BatchStore(keep_seconds=1800)
    store.add(new_job([row_holding(n, bytes(100)) for n in range(2, 6)], [], []))  # holds 400
    assert store.seconds_until_room(100, cap=500) == 0
    # 300 more needs 200 freed: the first two labels must be checked.
    assert store.seconds_until_room(300, cap=500) == 2 * SECONDS_PER_LABEL
    store.add(new_job([row_holding(2, bytes(100))], [], []))  # a second batch, waiting its turn
    assert store.seconds_until_room(500, cap=500) == 5 * SECONDS_PER_LABEL


def test_checked_labels_make_room():
    store = BatchStore(keep_seconds=1800)
    job = new_job([good_row(2), good_row(3)], [], [])
    store.add(job)
    held = sum(store.waiting_sizes())
    assert held == 2 * FRONT.stat().st_size
    assert store.seconds_until_room(held, cap=held) > 0
    run(job)
    assert store.waiting_sizes() == []
    assert store.seconds_until_room(held, cap=held) == 0


# In a batch, Tesseract reads only the picture with the warning, for its second reading.


@pytest.mark.skipif(not tesseract_available(), reason="Tesseract is not installed")
def test_a_batch_catches_a_warning_the_ai_reader_read_as_it_should_be():
    """The sample's warning is printed with wrong wording. If the AI reader returns the
    required text instead, as Claude did with a misspelt word on a real label, Tesseract's
    reading of the picture still disagrees."""
    entry = next(e for e in EXPECTED if e["id"] == "heronmere-gin-warning-wording")
    corrected = perfect_reading(entry["truth"]).model_copy(deep=True)
    corrected.government_warning.text = GOVERNMENT_WARNING
    application = application_for(entry)
    name = entry["images"][0]
    row = ApplicationRow(2, (name,), application, (), application.brand_name)
    job = new_job([MatchedRow(row, ((name, (LABELS_DIR / name).read_bytes()),), ())], [], [])
    run(job, ReplayReader(corrected))
    outcome = job.items[0].outcome
    assert outcome.second_reading
    warning = next(f for f in outcome.result.fields if f.field == "government_warning")
    assert warning.status == Status.REVIEW
    assert any(c.reason.startswith("Two readings of the warning disagree") for c in warning.checks)


def test_a_batch_reads_only_the_picture_with_the_warning(monkeypatch):
    read = []

    def passes(pictures):
        read.append(len(pictures))
        return [[[], []] for _ in pictures]

    monkeypatch.setattr("app.checking.ocr_passes", passes)
    monkeypatch.setattr("app.checking.tesseract_available", lambda: True)
    reading = recorded_reading().model_copy(deep=True)
    reading.government_warning.image_number = 2
    row = ApplicationRow(2, ("front.png", "back.png"), OLD_TOM, (), OLD_TOM.brand_name)
    pictures = (("front.png", FRONT.read_bytes()), ("back.png", FRONT.read_bytes()))
    job = new_job([MatchedRow(row, pictures, ())], [], [])
    run(job, ReplayReader(reading))
    assert read == [1]
    assert job.items[0].outcome.second_reading


def test_wait_estimates_are_not_shorter_than_measured_batches():
    """Measured on Azure with 2 CPUs on Oct 20, 2026: 31 labels in 32.7 s at the slowest,
    with the warning's second reading. Telling a visitor to come back too soon wastes a trip."""
    assert SECONDS_PER_LABEL >= 32.7 / 31


def test_every_picture_of_a_label_is_kept_smaller_for_review():
    from io import BytesIO

    from PIL import Image

    from app.batch import PREVIEW_EDGE

    row = ApplicationRow(2, ("front.png", "back.png"), OLD_TOM, (), OLD_TOM.brand_name)
    pictures = (("front.png", FRONT.read_bytes()), ("back.png", FRONT.read_bytes()))
    job = new_job([MatchedRow(row, pictures, ())], [], [])
    run(job)
    previews = job.items[0].previews
    assert len(previews) == 2
    for preview in previews:
        assert max(Image.open(BytesIO(preview)).size) == PREVIEW_EDGE == 900


def test_a_finished_batch_gives_its_total_time_and_the_average_per_label():
    from app.presenting import batch_view

    times = iter([100.0, 131.0])
    job = new_job([good_row(2), good_row(3)], [], [])

    async def go():
        await run_job(job, ReplayReader(), 1568, 4, asyncio.Semaphore(1), clock=lambda: next(times))

    asyncio.run(go())
    view = batch_view(job)
    assert view["timing"] == "Checked 2 labels in 31 seconds, about 15.5 seconds a label."
    assert all("seconds" not in item for item in view["items"])


def test_a_running_batch_gives_no_time_yet():
    from app.presenting import batch_view

    job = new_job([good_row(2)], [], [])
    assert batch_view(job)["timing"] is None


@pytest.mark.parametrize(
    ("seconds", "said"),
    [
        (0.4, "1 second"),
        (1, "1 second"),
        (45, "45 seconds"),
        (60, "1 minute"),
        (292, "4 minutes 52 seconds"),
    ],
)
def test_batch_times_read_naturally(seconds, said):
    from app.presenting import duration

    assert duration(seconds) == said


def test_a_very_fast_batch_says_under_a_tenth_of_a_second_a_label():
    from app.presenting import batch_view

    times = iter([100.0, 101.0])
    job = new_job([good_row(n) for n in range(2, 33)], [], [])

    async def go():
        await run_job(job, ReplayReader(), 1568, 8, asyncio.Semaphore(1), clock=lambda: next(times))

    asyncio.run(go())
    assert batch_view(job)["timing"] == "Checked 31 labels in 1 second, under 0.1 seconds a label."
