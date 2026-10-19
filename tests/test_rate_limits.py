from datetime import date

from app.limits import Limits, visitor_id


class FakeClock:
    def __init__(self):
        self.now = 0.0
        self.day = date(2026, 10, 19)

    def __call__(self):
        return self.now


def limits(checks=3, batches=2, per_day=100):
    clock = FakeClock()
    made = Limits(checks, 600, batches, 3600, per_day, clock=clock, today=lambda: clock.day)
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
    clock.day = date(2026, 10, 20)
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


def test_visitor_is_the_last_forwarded_address():
    # A visitor can put anything in X-Forwarded-For; Azure's ingress appends the real address.
    headers = {"x-forwarded-for": "1.2.3.4, 203.0.113.9"}
    assert visitor_id(headers, "10.0.0.1") == "203.0.113.9"
    assert visitor_id({}, "10.0.0.1") == "10.0.0.1"
    assert visitor_id({}, None) == "unknown"
