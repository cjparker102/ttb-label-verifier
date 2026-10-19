"""Result types shared by every rule."""

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum


class Status(StrEnum):
    PASS = "pass"
    REVIEW = "review"
    FAIL = "fail"
    NOT_NEEDED = "not_needed"


SEVERITY = {Status.NOT_NEEDED: 0, Status.PASS: 1, Status.REVIEW: 2, Status.FAIL: 3}


@dataclass(frozen=True)
class Citation:
    section: str  # for example "27 CFR 16.21"
    url: str
    checked: str  # date the eCFR text was last checked, YYYY-MM-DD


@dataclass(frozen=True)
class Check:
    status: Status
    reason: str  # one plain sentence for the agent
    note: str | None = None  # short tag on a pass, such as "Matches, different capitals"
    citation: Citation | None = None


def worst(statuses: Iterable[Status]) -> Status:
    """The most serious status in the list. An empty list counts as a pass."""
    return max(statuses, key=SEVERITY.__getitem__, default=Status.PASS)
