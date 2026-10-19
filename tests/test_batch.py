import asyncio

from app.batch import BatchStore, ItemState, new_job, run_job
from app.intake.matching import MatchedRow
from app.intake.spreadsheet import ApplicationRow
from app.rules.application import Application, BeverageType
from app.rules.results import Status
from tests.stand_ins import FailingReader, ReplayReader
from tools.make_samples import LABELS_DIR

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
        assert item.preview.startswith(b"\xff\xd8")  # a small JPEG kept for the page
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
