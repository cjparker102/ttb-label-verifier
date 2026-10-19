import pytest

from app.limits import Limits
from app.main import app


def roomy_limits() -> Limits:
    return Limits(1000, 600, 1000, 3600, 100_000)


@pytest.fixture(autouse=True)
def fresh_limits():
    """Every web test starts with empty usage counts, so tests don't affect each other."""
    saved = app.state.limits
    app.state.limits = roomy_limits()
    yield
    app.state.limits = saved
