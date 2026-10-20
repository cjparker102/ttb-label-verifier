"""A slow answer is asked for again, and whichever answer comes first is used (HedgedReader).

These use real waits, kept short: the reader asks again after AFTER seconds.
"""

import asyncio
import logging
import time

import pytest

from app.reading.claude import ReadingFailed, ReadResult
from app.reading.providers import HedgedReader
from tests.stand_ins import recorded_reading

READING = recorded_reading()
AFTER = 0.05
NEVER = 30  # longer than any test runs; such a request is always cancelled


class Scripted:
    """Answers each request after its own wait, with a result or an error, and notes
    which requests were cancelled before they finished."""

    def __init__(self, *plans):
        self.plans = plans  # (seconds, input tokens or an error), one per request
        self.sent = 0
        self.cancelled: list[int] = []

    async def read(self, images: list[bytes]) -> ReadResult:
        number = self.sent
        self.sent += 1
        seconds, answer = self.plans[number]
        try:
            await asyncio.sleep(seconds)
        except asyncio.CancelledError:
            self.cancelled.append(number)
            raise
        if isinstance(answer, Exception):
            raise answer
        return ReadResult(READING, seconds=seconds, input_tokens=answer, output_tokens=answer // 10)


def read(reader: Scripted) -> ReadResult:
    async def go():
        try:
            return await HedgedReader(reader, after=AFTER).read([b"picture"])
        finally:
            await asyncio.sleep(0)  # let a cancelled request see its cancellation

    return asyncio.run(go())


def test_a_quick_answer_is_used_without_asking_again():
    reader = Scripted((0, 1000))
    result = read(reader)
    assert reader.sent == 1
    assert (result.requests, result.input_tokens, result.output_tokens) == (1, 1000, 100)


def test_a_slow_answer_is_asked_for_again_and_the_quicker_answer_is_used():
    reader = Scripted((NEVER, 1000), (0, 3000))
    start = time.perf_counter()
    result = read(reader)
    assert time.perf_counter() - start < 1
    assert reader.sent == 2
    assert reader.cancelled == [0]  # the slow request is stopped
    assert result.requests == 2
    # The second request answered, and both are counted in the cost.
    assert (result.input_tokens, result.output_tokens) == (6000, 600)
    assert AFTER <= result.seconds < 1  # from the first request, not the second


def test_the_first_answer_is_used_if_it_still_comes_first():
    reader = Scripted((AFTER * 2, 1000), (NEVER, 3000))
    result = read(reader)
    assert reader.cancelled == [1]
    assert (result.requests, result.input_tokens) == (2, 2000)


def test_a_quick_failure_is_not_asked_for_again():
    reader = Scripted((0, ReadingFailed("refusal")))
    with pytest.raises(ReadingFailed):
        read(reader)
    assert reader.sent == 1


def test_a_slow_failure_waits_for_the_second_answer():
    reader = Scripted((AFTER * 2, ReadingFailed("refusal")), (AFTER * 4, 3000))
    result = read(reader)
    assert (result.requests, result.input_tokens) == (2, 6000)


def test_when_both_requests_fail_the_check_gets_the_error():
    reader = Scripted((AFTER * 2, ReadingFailed("first")), (AFTER * 3, ReadingFailed("second")))
    with pytest.raises(ReadingFailed, match="first"):
        read(reader)


def test_both_requests_stop_if_the_check_itself_is_cancelled():
    reader = Scripted((NEVER, 1000), (NEVER, 3000))

    async def visitor_leaves():
        check = asyncio.create_task(HedgedReader(reader, after=AFTER).read([b"picture"]))
        await asyncio.sleep(AFTER * 2)
        check.cancel()
        with pytest.raises(asyncio.CancelledError):
            await check
        await asyncio.sleep(0)

    asyncio.run(visitor_leaves())
    assert sorted(reader.cancelled) == [0, 1]


def test_asking_again_is_logged_without_label_details(caplog):
    with caplog.at_level(logging.WARNING, logger="ttb_label_verifier"):
        read(Scripted((NEVER, 1000), (0, 3000)))
    [record] = caplog.records
    assert "the label was read again" in record.getMessage()
    assert "The second request answered first" in record.getMessage()
    assert "OLD TOM" not in caplog.text
