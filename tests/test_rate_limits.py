from datetime import UTC, datetime

import pytest

from app.config import Settings
from app.limits import Limits, how_long, visitor_id
from app.samples import sample_labels


class FakeClock:
    def __init__(self):
        self.now = 0.0
        self.wall = datetime(2026, 10, 19, 12, 0, tzinfo=UTC)

    def __call__(self):
        return self.now


def limits(checks=3, batches=2, per_day=100):
    clock = FakeClock()
    made = Limits(checks, 600, batches, 3600, per_day, clock=clock, now=lambda: clock.wall)
    return made, clock


def test_a_visitor_may_check_up_to_the_limit():
    rate, _ = limits(checks=3)
    assert [rate.take_check("a") for _ in range(3)] == [None, None, None]
    assert "limit for this demo" in rate.take_check("a")


def test_visitors_are_counted_separately():
    rate, _ = limits(checks=1)
    assert rate.take_check("a") is None
    assert rate.take_check("b") is None
    assert rate.take_check("a") is not None


def test_the_window_slides():
    rate, clock = limits(checks=2)
    rate.take_check("a")
    clock.now = 300
    rate.take_check("a")
    assert rate.take_check("a") is not None
    clock.now = 600  # the first check is now 10 minutes old
    assert rate.take_check("a") is None


def test_daily_cap_covers_everyone_and_resets_next_day():
    rate, clock = limits(checks=100, per_day=2)
    assert rate.take_check("a") is None
    assert rate.take_check("b") is None
    assert "limit of 2 labels for today" in rate.take_check("c")
    clock.wall = datetime(2026, 10, 20, 0, 0, tzinfo=UTC)
    assert rate.take_check("c") is None


def test_refused_checks_are_not_counted():
    rate, _ = limits(checks=1, per_day=5)
    rate.take_check("a")
    for _ in range(3):
        rate.take_check("a")  # refused
    assert rate.daily.used == 1


def test_batches_have_their_own_visitor_limit():
    rate, _ = limits(checks=1, batches=2)
    assert rate.take_check("a") is None
    assert rate.take_batch("a", 10) is None  # a used-up check allowance doesn't block batches
    assert rate.take_batch("a", 10) is None
    assert "2 batches" in rate.take_batch("a", 10)


def test_batches_and_checks_share_the_daily_cap():
    rate, _ = limits(checks=10, batches=10, per_day=12)
    assert rate.take_batch("a", 10) is None
    assert rate.take_check("b") is None
    message = rate.take_batch("c", 5)
    assert "can check only 1 more today" in message
    assert rate.daily.used == 11  # the refused batch was not counted


def test_a_refused_check_says_how_long_to_wait():
    rate, clock = limits(checks=2)
    rate.take_check("a")
    clock.now = 300
    rate.take_check("a")
    clock.now = 420  # the first check leaves the 10-minute window at 600
    assert rate.take_check("a").endswith("Please wait 3 minutes and try again.")
    clock.now = 599.5
    assert rate.take_check("a").endswith("Please wait 1 minute and try again.")


def test_a_refused_batch_says_how_long_to_wait():
    rate, clock = limits(batches=2)
    rate.take_batch("a", 5)
    clock.now = 1000
    rate.take_batch("a", 5)
    clock.now = 1200  # the first batch leaves the hour's window at 3600
    assert rate.take_batch("a", 5).endswith("Please wait 40 minutes and try again.")


def test_the_daily_limit_says_when_it_starts_again():
    rate, clock = limits(checks=10, per_day=1)
    clock.wall = datetime(2026, 10, 19, 18, 10, tzinfo=UTC)
    rate.take_check("a")
    assert rate.take_check("b").endswith("Please try again in 6 hours, after midnight UTC.")
    assert rate.take_batch("b", 5).endswith("Please try again in 6 hours, after midnight UTC.")
    clock.wall = datetime(2026, 10, 19, 23, 30, tzinfo=UTC)
    assert rate.take_check("b").endswith("in 30 minutes, after midnight UTC.")


def test_a_batch_bigger_than_what_is_left_today_says_when_it_starts_again():
    rate, clock = limits(per_day=10)
    clock.wall = datetime(2026, 10, 19, 23, 0, tzinfo=UTC)
    assert rate.take_batch("a", 20).endswith(
        "Please send a smaller batch, or try again in 60 minutes, after midnight UTC."
    )


@pytest.mark.parametrize(
    ("seconds", "words"),
    [
        (0, "1 minute"),
        (30, "1 minute"),
        (60, "1 minute"),
        (61, "2 minutes"),
        (90 * 60, "90 minutes"),
        (90 * 60 + 1, "2 hours"),
        (5 * 3600 + 50 * 60, "6 hours"),  # rounded up, never too short
    ],
)
def test_waits_are_said_in_plain_words(seconds, words):
    assert how_long(seconds) == words


def test_a_new_visitor_can_try_every_sample_and_then_the_sample_batch():
    rate = Limits.from_settings(Settings())
    samples = len(sample_labels())
    assert all(rate.take_check("a") is None for _ in range(samples))
    assert rate.take_batch("a", samples) is None
    # And a whole office on one address has room for many more.
    assert rate.checks.limit >= 300


def test_an_office_on_one_address_can_send_30_batches_an_hour():
    rate = Limits.from_settings(Settings())
    assert all(rate.take_batch("office", 10) is None for _ in range(30))
    assert rate.take_batch("office", 10).endswith("Please wait 60 minutes and try again.")


def test_visitor_is_the_last_forwarded_address():
    # A visitor can put anything in X-Forwarded-For; Azure's ingress appends the real address.
    headers = {"x-forwarded-for": "1.2.3.4, 203.0.113.9"}
    assert visitor_id(headers, "10.0.0.1") == "203.0.113.9"
    assert visitor_id({}, "10.0.0.1") == "10.0.0.1"
    assert visitor_id({}, None) == "unknown"
