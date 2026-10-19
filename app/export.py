"""Batch results as an Excel file, built entirely in memory.

XlsxWriter's in_memory mode builds the file without temporary files (openpyxl
writes temporary files when saving). Every piece of text goes through
write_string(), and strings_to_formulas is off as well, so label or application
text starting with "=" can never become a formula in the agent's Excel.
"""

from io import BytesIO

import xlsxwriter

from app.batch import BatchJob, ItemState
from app.presenting import STATUS_VIEW, summary
from app.rules.results import Status

FILL_COLORS = {Status.FAIL: "#FDE8EA", Status.REVIEW: "#FFF3D6", Status.PASS: "#E7F4EC"}
NOT_CHECKED_COLOR = "#E5E7EB"


class Sheet:
    def __init__(self, workbook, name: str, headings: list[str], widths: list[int]):
        self.sheet = workbook.add_worksheet(name)
        self.formats = {
            color: workbook.add_format({"text_wrap": True, "valign": "top", "bg_color": color})
            for color in (*FILL_COLORS.values(), NOT_CHECKED_COLOR)
        }
        self.plain = workbook.add_format({"text_wrap": True, "valign": "top"})
        bold = workbook.add_format({"bold": True, "text_wrap": True, "valign": "top"})
        for column, (heading, width) in enumerate(zip(headings, widths, strict=True)):
            self.sheet.write_string(0, column, heading, bold)
            self.sheet.set_column(column, column, width)
        self.sheet.freeze_panes(1, 0)
        self.next_row = 1

    def add(self, values: list, fill: dict[int, str] | None = None) -> None:
        """Add a row. `fill` maps a column number to a background color."""
        for column, value in enumerate(values):
            style = self.formats[fill[column]] if fill and column in fill else self.plain
            if isinstance(value, int):
                self.sheet.write_number(self.next_row, column, value, style)
            else:
                self.sheet.write_string(self.next_row, column, value, style)
        self.next_row += 1


def results_workbook(job: BatchJob) -> bytes:
    out = BytesIO()
    workbook = xlsxwriter.Workbook(
        out,
        {
            "in_memory": True,
            "strings_to_formulas": False,
            "strings_to_urls": False,
            "strings_to_numbers": False,
        },
    )
    overview = Sheet(
        workbook,
        "Summary",
        ["Row", "Brand (application)", "Pictures", "Overall result", "What to look at", "Read by"],
        [7, 28, 34, 22, 80, 22],
    )
    details = Sheet(
        workbook,
        "Details",
        ["Row", "Brand (application)", "Field", "Application says", "Label says", "Result",
         "Reason", "Rule"],
        [7, 28, 22, 30, 40, 22, 60, 20],
    )  # fmt: skip

    for item in sorted(job.items, key=lambda i: i.row_number):
        first = [item.row_number, item.brand, "; ".join(item.file_names)]
        if item.state != ItemState.DONE or item.outcome is None:
            overview.add([*first, "Not checked", item.problem or "", ""], {3: NOT_CHECKED_COLOR})
            continue
        result = item.outcome.result
        to_look_at = [
            f"{field.title}: {check.reason}"
            for field in result.fields
            for check in field.checks
            if check.status in (Status.FAIL, Status.REVIEW)
        ]
        overall = " / ".join(line["text"] for line in summary(result.counts))
        read_by = "Basic text reading" if item.outcome.read_by == "ocr" else "AI reader"
        overview.add(
            [*first, overall, "\n".join(to_look_at), read_by],
            {3: FILL_COLORS.get(result.status, NOT_CHECKED_COLOR)},
        )

        for field in result.fields:
            problems = [c for c in field.checks if c.status in (Status.FAIL, Status.REVIEW)]
            shown = problems or [field.checks[0]]
            word = STATUS_VIEW[field.status]["word"]
            if field.status == Status.PASS and field.notes:
                word = field.notes[0]
            said = (
                "The required warning text"
                if field.field == "government_warning"
                else field.application_says
            )
            details.add(
                [
                    item.row_number,
                    item.brand,
                    field.title,
                    said,
                    field.label_says or "Not found on the label",
                    word,
                    " ".join(c.reason for c in shown),
                    ", ".join(c.citation.section for c in shown if c.citation),
                ],
                {5: FILL_COLORS[field.status]} if field.status in FILL_COLORS else None,
            )

    workbook.close()
    return out.getvalue()
