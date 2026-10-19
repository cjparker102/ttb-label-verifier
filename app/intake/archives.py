"""Takes label pictures out of a ZIP file, in memory, with safety limits.

Nothing is ever extracted to disk, so a path like "../../evil" could not escape
anyway; such entries are still refused and reported, so the user knows.
"""

import io
import stat
import zipfile
from dataclasses import dataclass, field

from app.intake.images import FORMATS, image_kind

MB = 1024 * 1024
MAX_ITEMS = 2000  # entries listed in the ZIP, pictures or not
MAX_PICTURES = 600
MAX_PICTURE_BYTES = 50 * MB  # one picture, unpacked
MAX_TOTAL_BYTES = 400 * MB  # everything unpacked; the app holds it in memory
MAX_RATIO = 100  # pictures barely compress; far more than this is a zip bomb sign

ARCHIVE_ENDINGS = (".zip", ".7z", ".rar", ".tar", ".gz", ".tgz", ".bz2", ".xz")
ARCHIVE_SIGNATURES = (b"PK\x03\x04", b"7z\xbc\xaf\x27\x1c", b"Rar!", b"\x1f\x8b")
CLUTTER = ("__macosx/", ".ds_store", "thumbs.db", "desktop.ini")


class ArchiveError(ValueError):
    """The whole archive can't be used. The message says why, in plain words."""


@dataclass(frozen=True)
class Skipped:
    name: str
    reason: str


@dataclass
class Unpacked:
    pictures: dict[str, bytes] = field(default_factory=dict)  # by file name, without folders
    skipped: list[Skipped] = field(default_factory=list)


def base_name(path: str) -> str:
    return path.replace("\\", "/").rstrip("/").rsplit("/", 1)[-1]


def is_unsafe_path(path: str) -> bool:
    parts = path.replace("\\", "/").split("/")
    return (
        path.startswith(("/", "\\"))
        or ".." in parts
        or (len(path) > 1 and path[1] == ":")  # a Windows drive letter
        or "\x00" in path
    )


def is_clutter(path: str) -> bool:
    lowered = path.replace("\\", "/").casefold()
    return any(marker in lowered for marker in CLUTTER) or base_name(lowered).startswith("._")


def is_link(entry: zipfile.ZipInfo) -> bool:
    return stat.S_ISLNK(entry.external_attr >> 16)


def problem_with(entry: zipfile.ZipInfo) -> str | None:
    """Why an entry must be skipped before it is even opened, if it must."""
    name = entry.filename
    if is_clutter(name):
        return "A system file, not a picture."
    if is_unsafe_path(name):
        return "Its folder path points outside the archive, so it was not opened."
    if is_link(entry):
        return "A link to another file, not a picture."
    if entry.flag_bits & 0x1:
        return "Password-protected, so it can't be opened."
    if name.casefold().endswith(ARCHIVE_ENDINGS):
        return "An archive inside the archive. Archives inside archives are not opened."
    if entry.file_size > MAX_PICTURE_BYTES:
        return f"Larger than {MAX_PICTURE_BYTES // MB} MB when unpacked."
    if entry.file_size > MAX_RATIO * max(entry.compress_size, 1):
        return "Packed far more tightly than any picture could be, so it was not opened."
    return None


def unpack_zip(data: bytes) -> Unpacked:
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as error:
        raise ArchiveError("This ZIP file could not be opened.") from error

    with archive:
        entries = [entry for entry in archive.infolist() if not entry.is_dir()]
        if len(entries) > MAX_ITEMS:
            raise ArchiveError(
                f"This ZIP file holds {len(entries):,} items. The limit is {MAX_ITEMS:,}."
            )
        unpacked = Unpacked()
        seen: set[str] = set()
        total = 0
        for entry in entries:
            name = base_name(entry.filename)
            reason = problem_with(entry)
            if reason:
                unpacked.skipped.append(Skipped(entry.filename, reason))
                continue
            if total + entry.file_size > MAX_TOTAL_BYTES:
                raise ArchiveError(
                    f"Unpacked, this ZIP file would be larger than {MAX_TOTAL_BYTES // MB:,} MB."
                )
            try:
                with archive.open(entry) as member:
                    # Read at most one byte past the limit, in case the size in the header lies.
                    content = member.read(MAX_PICTURE_BYTES + 1)
            except (NotImplementedError, zipfile.BadZipFile, RuntimeError, OSError):
                unpacked.skipped.append(Skipped(entry.filename, "This file could not be unpacked."))
                continue
            total += len(content)
            if len(content) > MAX_PICTURE_BYTES:
                unpacked.skipped.append(
                    Skipped(
                        entry.filename, f"Larger than {MAX_PICTURE_BYTES // MB} MB when unpacked."
                    )
                )
                continue
            if content.startswith(ARCHIVE_SIGNATURES):
                unpacked.skipped.append(
                    Skipped(
                        entry.filename,
                        "An archive inside the archive. Archives inside archives are not opened.",
                    )
                )
                continue
            if image_kind(content) is None:
                unpacked.skipped.append(
                    Skipped(entry.filename, f"Not a picture or PDF this app can read ({FORMATS}).")
                )
                continue
            if name.casefold() in seen:
                unpacked.skipped.append(
                    Skipped(entry.filename, f'Another picture is also named "{name}".')
                )
                continue
            if len(unpacked.pictures) == MAX_PICTURES:
                raise ArchiveError(f"This ZIP file holds more than {MAX_PICTURES} pictures.")
            seen.add(name.casefold())
            unpacked.pictures[name] = content
    return unpacked


def collect_pictures(files: list[tuple[str, bytes]]) -> Unpacked:
    """Gather the pictures from a batch upload: loose pictures, ZIP files, or both."""
    collected = Unpacked()
    seen: set[str] = set()

    def add(name: str, content: bytes, shown: str) -> None:
        if name.casefold() in seen:
            collected.skipped.append(Skipped(shown, f'Another picture is also named "{name}".'))
            return
        if len(collected.pictures) == MAX_PICTURES:
            raise ArchiveError(f"This upload holds more than {MAX_PICTURES} pictures.")
        seen.add(name.casefold())
        collected.pictures[name] = content

    for name, data in files:
        if data.startswith(b"PK\x03\x04") or name.casefold().endswith(".zip"):
            unpacked = unpack_zip(data)
            collected.skipped += [Skipped(f"{name}: {s.name}", s.reason) for s in unpacked.skipped]
            for inner, content in unpacked.pictures.items():
                add(inner, content, f"{name}: {inner}")
        elif image_kind(data):
            add(base_name(name), data, name)
        else:
            collected.skipped.append(
                Skipped(name, f"Not a picture this app can read ({FORMATS}), or a ZIP file.")
            )
    return collected
