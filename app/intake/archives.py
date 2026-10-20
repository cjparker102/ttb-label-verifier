"""Takes label pictures out of ZIP and 7z files, in memory, with safety limits.

Nothing is ever extracted to disk, so a path like "../../evil" could not escape
anyway; such entries are still refused and reported, so the user knows.
"""

import dataclasses
import io
import stat
import zipfile
from dataclasses import dataclass, field

import py7zr
import py7zr.exceptions
import py7zr.io

from app.intake.images import FORMATS, image_kind
from app.intake.spreadsheet import SpreadsheetFile

MB = 1024 * 1024
MAX_ITEMS = 2000  # entries listed in the ZIP, pictures or not
MAX_PICTURES = 600
MAX_PICTURE_BYTES = 50 * MB  # one picture, unpacked
MAX_TOTAL_BYTES = 400 * MB  # everything unpacked; the app holds it in memory
MAX_RATIO = 100  # pictures barely compress; far more than this is a zip bomb sign

ARCHIVE_ENDINGS = (".zip", ".7z", ".rar", ".tar", ".gz", ".tgz", ".bz2", ".xz")
SEVEN_ZIP = b"7z\xbc\xaf\x27\x1c"
ARCHIVE_SIGNATURES = (b"PK\x03\x04", SEVEN_ZIP, b"Rar!", b"\x1f\x8b")
CLUTTER = ("__macosx/", ".ds_store", "thumbs.db", "desktop.ini")
SPREADSHEET_ENDINGS = (".csv", ".xlsx")


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
    # Spreadsheets found in a ZIP or 7z file. One may be the batch's spreadsheet.
    spreadsheets: list[SpreadsheetFile] = field(default_factory=list)


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
    # "._" files are Mac file details; "~$" files are Office's lock files.
    return any(marker in lowered for marker in CLUTTER) or base_name(lowered).startswith(
        ("._", "~$")
    )


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
            keep(unpacked, seen, entry.filename, content, "ZIP")
    return unpacked


NESTED = "An archive inside the archive. Archives inside archives are not opened."


def keep(unpacked: Unpacked, seen: set[str], path: str, content: bytes, kind: str) -> None:
    """The checks every unpacked file gets, whatever archive it came from."""
    name = base_name(path)
    if len(content) > MAX_PICTURE_BYTES:
        unpacked.skipped.append(
            Skipped(path, f"Larger than {MAX_PICTURE_BYTES // MB} MB when unpacked.")
        )
    elif name.casefold().endswith(SPREADSHEET_ENDINGS):  # before the archive check: .xlsx is a ZIP
        unpacked.spreadsheets.append(SpreadsheetFile(path, content))
    elif content.startswith(ARCHIVE_SIGNATURES):
        unpacked.skipped.append(Skipped(path, NESTED))
    elif image_kind(content) is None:
        unpacked.skipped.append(
            Skipped(path, f"Not a picture or PDF this app can read ({FORMATS}).")
        )
    elif name.casefold() in seen:
        unpacked.skipped.append(Skipped(path, f'Another picture is also named "{name}".'))
    elif len(unpacked.pictures) == MAX_PICTURES:
        raise ArchiveError(f"This {kind} file holds more than {MAX_PICTURES} pictures.")
    else:
        seen.add(name.casefold())
        unpacked.pictures[name] = content


class OverLimit(Exception):
    pass


class CappedWriter(py7zr.io.Py7zIO):
    """Collects one unpacked file in memory, and stops the unpacking as soon as the
    file, or the archive as a whole, goes over its limit."""

    def __init__(self, budget: list[int]):
        self.buffer = io.BytesIO()
        self.budget = budget  # bytes the whole archive may still unpack, shared

    def write(self, data: bytes | bytearray) -> int:
        if self.buffer.tell() + len(data) > MAX_PICTURE_BYTES or len(data) > self.budget[0]:
            raise OverLimit
        self.budget[0] -= len(data)
        return self.buffer.write(data)

    def read(self, size: int | None = None) -> bytes:
        return self.buffer.read(size)

    def seek(self, offset: int, whence: int = 0) -> int:
        return self.buffer.seek(offset, whence)

    def flush(self) -> None:
        self.buffer.flush()

    def size(self) -> int:
        return len(self.buffer.getbuffer())


class CappedFactory(py7zr.io.WriterFactory):
    def __init__(self):
        self.budget = [MAX_TOTAL_BYTES]
        self.files: dict[str, CappedWriter] = {}

    def create(self, filename: str) -> CappedWriter:
        self.files[filename] = CappedWriter(self.budget)
        return self.files[filename]


def unpack_7z(data: bytes) -> Unpacked:
    """Like unpack_zip, for 7z files. 7z often packs files together ("solid"), so the
    zip bomb check compares the whole archive's listed size with its real size."""
    try:
        archive = py7zr.SevenZipFile(io.BytesIO(data), mode="r")
    except (py7zr.exceptions.ArchiveError, py7zr.exceptions.PasswordRequired, OSError) as error:
        if isinstance(error, py7zr.exceptions.PasswordRequired):
            raise ArchiveError(
                "This 7z file is password-protected, so it can't be opened."
            ) from error
        raise ArchiveError("This 7z file could not be opened.") from error

    unpacked = Unpacked()
    with archive:
        if archive.needs_password():
            raise ArchiveError("This 7z file is password-protected, so it can't be opened.")
        listing = [info for info in archive.list() if not info.is_directory]
        if len(listing) > MAX_ITEMS:
            raise ArchiveError(
                f"This 7z file holds {len(listing):,} items. The limit is {MAX_ITEMS:,}."
            )
        wanted = []
        for info in listing:
            path = info.filename
            reason = None
            if is_clutter(path):
                reason = "A system file, not a picture."
            elif is_unsafe_path(path):
                reason = "Its folder path points outside the archive, so it was not opened."
            elif info.is_symlink:
                reason = "A link to another file, not a picture."
            elif path.casefold().endswith(ARCHIVE_ENDINGS):
                reason = NESTED
            elif (info.uncompressed or 0) > MAX_PICTURE_BYTES:
                reason = f"Larger than {MAX_PICTURE_BYTES // MB} MB when unpacked."
            if reason:
                unpacked.skipped.append(Skipped(path, reason))
            else:
                wanted.append(info)
        listed = sum(info.uncompressed or 0 for info in wanted)
        if listed > MAX_TOTAL_BYTES:
            raise ArchiveError(
                f"Unpacked, this 7z file would be larger than {MAX_TOTAL_BYTES // MB:,} MB."
            )
        if listed > MAX_RATIO * len(data):
            raise ArchiveError(
                "This 7z file is packed far more tightly than pictures could be, "
                "so it was not opened."
            )
        if not wanted:
            return unpacked
        factory = CappedFactory()
        try:
            archive.extract(targets=[info.filename for info in wanted], factory=factory)
        except OverLimit as error:
            raise ArchiveError(
                "This 7z file unpacks to more than its listing says, so it was not opened."
            ) from error
        except (py7zr.exceptions.ArchiveError, py7zr.exceptions.PasswordRequired, OSError) as error:
            raise ArchiveError("This 7z file could not be unpacked.") from error

    seen: set[str] = set()
    for info in wanted:
        writer = factory.files.get(info.filename)
        content = writer.buffer.getvalue() if writer else b""
        keep(unpacked, seen, info.filename, content, "7z")
    return unpacked


def collect_pictures(files: list[tuple[str, bytes]]) -> Unpacked:
    """Gather the pictures from a batch upload: loose pictures, ZIP or 7z files, or both.
    Spreadsheets inside ZIP or 7z files are gathered too."""
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
        is_zip = data.startswith(b"PK\x03\x04") or name.casefold().endswith(".zip")
        is_7z = data.startswith(SEVEN_ZIP) or name.casefold().endswith(".7z")
        if is_zip or is_7z:
            unpacked = unpack_zip(data) if is_zip else unpack_7z(data)
            collected.skipped += [Skipped(f"{name}: {s.name}", s.reason) for s in unpacked.skipped]
            collected.spreadsheets += [
                dataclasses.replace(sheet, archive=name) for sheet in unpacked.spreadsheets
            ]
            for inner, content in unpacked.pictures.items():
                add(inner, content, f"{name}: {inner}")
        elif image_kind(data):
            add(base_name(name), data, name)
        else:
            collected.skipped.append(
                Skipped(name, f"Not a picture this app can read ({FORMATS}), or a ZIP or 7z file.")
            )
    return collected
