"""Batch jobs: many labels checked in the background, kept in memory for a short time.

A job holds each label's pictures only until that label is checked. After that it
keeps the results and a small preview, and the finished job is dropped after
`keep_seconds`. Nothing is written anywhere.
"""

import asyncio
import dataclasses
import logging
import secrets
import time
from dataclasses import dataclass, field
from enum import StrEnum

from app.checking import (
    CheckOutcome,
    LabelReader,
    NoReader,
    NotAnImage,
    TooManyPictures,
    check_one,
)
from app.intake.archives import Skipped
from app.intake.images import shrink_to_jpeg
from app.intake.matching import MatchedRow
from app.rules.application import Application

PREVIEW_EDGE = 320
# How long a batch takes for each label, for wait estimates. Measured on Azure on Oct 20,
# 2026, with Tesseract's second reading of the warning: 31 labels in 29.5 s and 32.7 s with
# 2 CPUs (about 1.0 s a label), and in 53.5 s and 55.7 s with 1 CPU (1.8 s). The app runs
# with 2 CPUs; the slowest measured rate plus a margin keeps estimates rarely too short.
# With 1 CPU, this would need to be about 2 seconds.
SECONDS_PER_LABEL = 1.2
log = logging.getLogger("ttb_label_verifier")


class ItemState(StrEnum):
    WAITING = "waiting"
    DONE = "done"
    NOT_CHECKED = "not_checked"


@dataclass
class BatchItem:
    row_number: int
    brand: str
    file_names: tuple[str, ...]
    state: ItemState
    problem: str | None = None  # why it was not checked
    outcome: CheckOutcome | None = None
    preview: bytes | None = None  # a small JPEG of the first picture


@dataclass
class Work:
    """A label waiting to be checked. Its pictures are let go once it is done."""

    item: BatchItem
    application: Application
    pictures: list[tuple[str, bytes]]


@dataclass
class BatchJob:
    id: str
    items: list[BatchItem]
    skipped_files: list[Skipped]
    unused_pictures: list[str]
    state: str = "queued"  # queued, running, finished
    finished_at: float | None = None
    notes: list[str] = field(default_factory=list)  # about the upload, such as which spreadsheet
    work: list[Work] = field(default_factory=list, repr=False)
    task: asyncio.Task | None = field(default=None, repr=False)

    @property
    def total(self) -> int:
        return len(self.items)

    @property
    def done(self) -> int:
        return sum(1 for item in self.items if item.state != ItemState.WAITING)


def picture_sizes(work: list[Work]) -> list[int]:
    """The bytes each label's pictures hold in memory. A picture used by two labels is
    held once, so it is counted once."""
    seen: set[int] = set()
    sizes = []
    for label in work:
        size = 0
        for _, data in label.pictures:
            if id(data) not in seen:
                seen.add(id(data))
                size += len(data)
        sizes.append(size)
    return sizes


def new_job(matched: list[MatchedRow], skipped: list[Skipped], unused: list[str]) -> BatchJob:
    items, work = [], []
    for match in matched:
        row = match.row
        item = BatchItem(row.row_number, row.brand_name, row.file_names, ItemState.WAITING)
        if row.problems:
            item.state, item.problem = ItemState.NOT_CHECKED, " ".join(row.problems)
        elif match.missing:
            names = ", ".join(match.missing)
            item.state = ItemState.NOT_CHECKED
            item.problem = f"These pictures were not in the upload: {names}."
        else:
            work.append(Work(item, row.application, list(match.pictures)))
        items.append(item)
    # The ID is the only key to the results, so it must be impossible to guess.
    return BatchJob(secrets.token_urlsafe(16), items, skipped, unused, work=work)


async def check_item(
    work: Work, reader: LabelReader | None, max_edge: int, ocr_fallback: bool
) -> None:
    item = work.item
    try:
        # Only the picture with the warning is read a second time, for the warning's check.
        outcome = await check_one(
            work.application, work.pictures, reader, max_edge, ocr_fallback, warning_only=True
        )
    except (NotAnImage, TooManyPictures) as error:
        item.state, item.problem = ItemState.NOT_CHECKED, str(error)
    except NoReader:
        item.state = ItemState.NOT_CHECKED
        item.problem = "The label reader could not read this label. Please check it on its own."
    else:
        item.preview = await asyncio.to_thread(shrink_to_jpeg, outcome.images[0], PREVIEW_EDGE)
        item.outcome = dataclasses.replace(outcome, images=[])
        item.state = ItemState.DONE
    finally:
        work.pictures = []


async def run_job(
    job: BatchJob,
    reader: LabelReader | None,
    max_edge: int,
    concurrency: int,
    one_at_a_time: asyncio.Semaphore,
    clock=time.monotonic,
    ocr_fallback: bool = True,
) -> None:
    """Check every waiting label. Only one batch runs at a time across the app."""
    async with one_at_a_time:
        job.state = "running"
        slots = asyncio.Semaphore(concurrency)

        async def one(work: Work) -> None:
            async with slots:
                await check_item(work, reader, max_edge, ocr_fallback)

        try:
            await asyncio.gather(*(one(work) for work in job.work))
        except Exception:
            log.exception("A batch stopped unexpectedly")
        finally:
            # Whatever happened, the batch ends, and nothing is left waiting forever.
            for item in job.items:
                if item.state == ItemState.WAITING:
                    item.state = ItemState.NOT_CHECKED
                    item.problem = "Something went wrong before this label was checked."
            job.work = []
            job.state = "finished"
            job.finished_at = clock()


class BatchStore:
    """Jobs by ID. Finished jobs are forgotten after keep_seconds."""

    def __init__(self, keep_seconds: float, clock=time.monotonic):
        self.keep_seconds = keep_seconds
        self.clock = clock
        self.jobs: dict[str, BatchJob] = {}

    def add(self, job: BatchJob) -> None:
        self.forget_old()
        self.jobs[job.id] = job

    def get(self, job_id: str) -> BatchJob | None:
        self.forget_old()
        return self.jobs.get(job_id)

    def waiting_sizes(self) -> list[int]:
        """The bytes held by each label not yet checked, in the order they will be checked:
        the running batch first, then the batches waiting their turn."""
        return [size for job in self.jobs.values() for size in picture_sizes(job.work)]

    def seconds_until_room(self, size: int, cap: int) -> float:
        """0 if a new batch holding `size` bytes of pictures, no more than `cap`, fits
        under `cap` now; otherwise about how long until enough labels ahead of it are
        checked."""
        sizes = self.waiting_sizes()
        over = sum(sizes) + size - cap
        labels = 0
        while over > 0 and labels < len(sizes):
            over -= sizes[labels]
            labels += 1
        return labels * SECONDS_PER_LABEL

    def forget_old(self) -> None:
        now = self.clock()
        old = [
            job_id
            for job_id, job in self.jobs.items()
            if job.finished_at is not None and now - job.finished_at > self.keep_seconds
        ]
        for job_id in old:
            del self.jobs[job_id]
