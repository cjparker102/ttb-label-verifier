import pytest

from app.limits import RateLimiter
from app.main import app


@pytest.fixture(autouse=True)
def fresh_rate_limits():
    """Every web test starts with empty rate-limit counts, so tests don't affect each other."""
    saved = app.state.limiter
    app.state.limiter = RateLimiter(per_visitor=1000, window_seconds=600, per_day=10_000)
    yield
    app.state.limiter = saved
