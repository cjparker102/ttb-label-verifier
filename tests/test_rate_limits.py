from datetime import date

from app.limits import RateLimiter, visitor_id


class FakeClock:
    def __init__(self):
        self.now = 0.0
        self.day = date(2026, 10, 19)

    def __call__(self):
        return self.now


def limiter(per_visitor=3, window_seconds=600, per_day=100):
    clock = FakeClock()
    return RateLimiter(
        per_visitor, window_seconds, per_day, clock=clock, today=lambda: clock.day
    ), clock


def test_a_visitor_may_check_up_to_the_limit():
    rate, _ = limiter(per_visitor=3)
    assert [rate.take("a") for _ in range(3)] == [None, None, None]
    assert "limit for this demo" in rate.take("a")


def test_visitors_are_counted_separately():
    rate, _ = limiter(per_visitor=1)
    assert rate.take("a") is None
    assert rate.take("b") is None
    assert rate.take("a") is not None


def test_the_window_slides():
    rate, clock = limiter(per_visitor=2, window_seconds=600)
    rate.take("a")
    clock.now = 300
    rate.take("a")
    assert rate.take("a") is not None
    clock.now = 600  # the first check is now 10 minutes old
    assert rate.take("a") is None


def test_daily_cap_covers_everyone_and_resets_next_day():
    rate, clock = limiter(per_visitor=100, per_day=2)
    assert rate.take("a") is None
    assert rate.take("b") is None
    message = rate.take("c")
    assert "limit of 2 labels for today" in message
    clock.day = date(2026, 10, 20)
    assert rate.take("c") is None


def test_refused_checks_are_not_counted():
    rate, _ = limiter(per_visitor=1, per_day=5)
    rate.take("a")
    for _ in range(3):
        rate.take("a")  # refused
    assert rate.used_today == 1


def test_visitor_is_the_last_forwarded_address():
    # A visitor can put anything in X-Forwarded-For; Azure's ingress appends the real address.
    headers = {"x-forwarded-for": "1.2.3.4, 203.0.113.9"}
    assert visitor_id(headers, "10.0.0.1") == "203.0.113.9"
    assert visitor_id({}, "10.0.0.1") == "10.0.0.1"
    assert visitor_id({}, None) == "unknown"
