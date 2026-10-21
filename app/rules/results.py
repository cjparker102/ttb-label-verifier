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
class WordChange:
    """One difference between required text and the label, for a track-changes view."""

    kind: str  # "missing", "extra", or "changed"
    required: str  # the words the rule requires ("" when words were added)
    found: str  # the words on the label ("" when words are missing)


@dataclass(frozen=True)
class Check:
    status: Status
    reason: str  # one plain sentence for the agent
    note: str | None = None  # short tag on a pass, such as "Matches, different capitals"
    citation: Citation | None = None
    changes: tuple[WordChange, ...] = ()
    confirmed: bool = True  # False for a pass on the AI reader's word alone, never shown as met


def worst(statuses: Iterable[Status]) -> Status:
    """The most serious status in the list. An empty list counts as a pass."""
    return max(statuses, key=SEVERITY.__getitem__, default=Status.PASS)
