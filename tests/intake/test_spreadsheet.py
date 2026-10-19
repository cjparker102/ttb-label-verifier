import io

import pytest
from openpyxl import Workbook

from app.intake.spreadsheet import MAX_ROWS, SpreadsheetError, read_spreadsheet
from app.rules.application import BeverageType
from tools.make_samples import PHOTOS, SAMPLES, SAMPLES_DIR

HEADINGS = [
    "file_names",
    "beverage_type",
    "brand_name",
    "class_type",
    "alcohol_content",
    "net_contents",
    "bottler_name_address",
    "country_of_origin",
]
OLD_TOM = [
    "front.png; back.png",
    "Distilled spirits",
    "OLD TOM DISTILLERY",
    "Kentucky Straight Bourbon Whiskey",
    "45%",
    "750 mL",
    "Old Tom Distillery, Bardstown, Kentucky",
    "",
]


def csv_bytes(rows, delimiter=",", encoding="utf-8"):
    text = "\n".join(delimiter.join(f'"{cell}"' for cell in row) for row in rows)
    return text.encode(encoding)


def xlsx_bytes(rows, percent_cells=()):
    workbook = Workbook()
    sheet = workbook.active
    for row in rows:
        sheet.append(row)
    for ref in percent_cells:
        sheet[ref].number_format = "0.0%"
    out = io.BytesIO()
    workbook.save(out)
    return out.getvalue()


def test_the_sample_applications_csv_reads_correctly():
    data = (SAMPLES_DIR / "applications.csv").read_bytes()
    rows = read_spreadsheet("applications.csv", data)
    assert len(rows) == len(SAMPLES) + len(PHOTOS)
    assert all(not row.problems for row in rows)
    old_tom = rows[0]
    assert old_tom.row_number == 2
    assert old_tom.file_names == ("old-tom-bourbon_front.png", "old-tom-bourbon_back.png")
    assert old_tom.application.beverage_type == BeverageType.DISTILLED_SPIRITS
    assert old_tom.application.country_of_origin == ""
    wine = next(r for r in rows if r.application.beverage_type == BeverageType.WINE)
    assert wine.application.brand_name == "Chateau Landrevin"


def test_headings_can_be_written_in_other_ways():
    headings = ["Files", "Type", "Brand", "Class/Type", "ABV", "Net Contents", "Bottler", "Country"]
    rows = read_spreadsheet("batch.csv", csv_bytes([headings, OLD_TOM]))
    assert rows[0].application.alcohol_content == "45%"
    assert rows[0].application.bottler_name_address == "Old Tom Distillery, Bardstown, Kentucky"


def test_missing_required_column_is_named():
    headings = [h for h in HEADINGS if h != "net_contents"]
    row = [c for h, c in zip(HEADINGS, OLD_TOM, strict=True) if h != "net_contents"]
    with pytest.raises(SpreadsheetError, match="net contents"):
        read_spreadsheet("batch.csv", csv_bytes([headings, row]))


def test_optional_columns_may_be_left_out():
    headings = [h for h in HEADINGS if h not in ("alcohol_content", "country_of_origin")]
    row = [c for h, c in zip(HEADINGS, OLD_TOM, strict=True) if h in headings]
    rows = read_spreadsheet("batch.csv", csv_bytes([headings, row]))
    assert rows[0].application.alcohol_content == ""


def test_row_problems_are_reported_by_row_number():
    bad_type = [*OLD_TOM[:1], "Cider", *OLD_TOM[2:]]
    no_brand = [*OLD_TOM[:2], "", *OLD_TOM[3:]]
    no_files = ["", *OLD_TOM[1:]]
    rows = read_spreadsheet(
        "batch.csv", csv_bytes([HEADINGS, OLD_TOM, bad_type, no_brand, no_files])
    )
    assert [r.row_number for r in rows] == [2, 3, 4, 5]
    assert rows[0].problems == ()
    assert rows[1].application is None
    assert 'Unknown beverage type "Cider"' in rows[1].problems[0]
    assert rows[2].problems == ("The brand name is blank.",)
    assert rows[3].problems == ("No picture file names are listed.",)


def test_blank_rows_are_skipped():
    rows = read_spreadsheet("batch.csv", csv_bytes([HEADINGS, [""] * 8, OLD_TOM, [""] * 8]))
    assert [r.row_number for r in rows] == [3]


def test_semicolon_separated_csv_from_european_excel():
    rows = read_spreadsheet("batch.csv", csv_bytes([HEADINGS, OLD_TOM], delimiter=";"))
    assert rows[0].file_names == ("front.png", "back.png")


def test_windows_excel_csv_with_accents():
    row = [*OLD_TOM[:2], "Château Landrevin", *OLD_TOM[3:]]
    data = csv_bytes([HEADINGS, row], encoding="cp1252")
    assert read_spreadsheet("batch.csv", data)[0].application.brand_name == "Château Landrevin"


def test_csv_with_a_byte_order_mark():
    data = b"\xef\xbb\xbf" + csv_bytes([HEADINGS, OLD_TOM])
    assert read_spreadsheet("batch.csv", data)[0].application is not None


def test_file_names_split_on_semicolons_and_new_lines():
    row = ["a.png;b.png\nc.png | d.png", *OLD_TOM[1:]]
    rows = read_spreadsheet("batch.csv", csv_bytes([HEADINGS, row]))
    assert rows[0].file_names == ("a.png", "b.png", "c.png", "d.png")


def test_excel_file_with_numbers_and_percent_cells():
    row = [*OLD_TOM[:4], 0.135, 750, *OLD_TOM[6:]]
    data = xlsx_bytes([HEADINGS, row], percent_cells=["E2"])
    application = read_spreadsheet("batch.xlsx", data)[0].application
    assert application.alcohol_content == "13.5%"
    assert application.net_contents == "750"


def test_too_many_rows():
    with pytest.raises(SpreadsheetError, match=f"up to {MAX_ROWS}"):
        read_spreadsheet("batch.csv", csv_bytes([HEADINGS, *([OLD_TOM] * (MAX_ROWS + 1))]))


@pytest.mark.parametrize(
    ("name", "data", "message"),
    [
        ("batch.pdf", b"%PDF", "not a spreadsheet"),
        ("batch.xlsx", b"not really excel", "could not be opened"),
        ("batch.csv", b"", "empty"),
        ("batch.csv", csv_bytes([HEADINGS]), "no applications"),
    ],
)
def test_unusable_files_say_why(name, data, message):
    with pytest.raises(SpreadsheetError, match=message):
        read_spreadsheet(name, data)


def test_reading_uploaded_spreadsheets_writes_nothing_to_disk():
    from tests.disk_watch import watch_disk_writes

    excel = xlsx_bytes([HEADINGS, *([OLD_TOM] * 50)], percent_cells=["E2"])
    text = csv_bytes([HEADINGS, *([OLD_TOM] * 50)])
    read_spreadsheet("batch.xlsx", excel)  # warm-up: loads any lazy imports
    read_spreadsheet("batch.csv", text)
    with watch_disk_writes() as writes:
        assert len(read_spreadsheet("batch.xlsx", excel)) == 50
        assert len(read_spreadsheet("batch.csv", text)) == 50
    assert list(writes) == []
