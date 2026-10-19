"""Matches spreadsheet rows to their pictures by file name."""

from dataclasses import dataclass

from app.intake.archives import base_name
from app.intake.spreadsheet import ApplicationRow


@dataclass(frozen=True)
class MatchedRow:
    row: ApplicationRow
    pictures: tuple[tuple[str, bytes], ...]  # (file name, bytes), in the order the row lists them
    missing: tuple[str, ...]  # file names the row lists that were not uploaded


def match_rows(
    rows: list[ApplicationRow], pictures: dict[str, bytes]
) -> tuple[list[MatchedRow], list[str]]:
    """Pair each row with its pictures, ignoring folders and capital letters.
    Also returns the pictures that no row lists."""
    by_name = {name.casefold(): name for name in pictures}
    used: set[str] = set()
    matched = []
    for row in rows:
        found, missing = [], []
        for listed in row.file_names:
            name = by_name.get(base_name(listed).casefold())
            if name is None:
                missing.append(listed)
            else:
                found.append((name, pictures[name]))
                used.add(name)
        matched.append(MatchedRow(row, tuple(found), tuple(missing)))
    unused = [name for name in pictures if name not in used]
    return matched, unused
