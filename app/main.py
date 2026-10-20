"""Web entry point for the TTB Label Verifier."""

import asyncio
import csv
import io
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.datastructures import UploadFile
from starlette.exceptions import HTTPException
from starlette.formparsers import MultiPartParser

from app.batch import BatchStore, new_job, picture_sizes, run_job
from app.checking import LabelReader, NoReader, NotAnImage, TooManyPictures, check_one
from app.config import MB, load_settings
from app.export import results_workbook
from app.intake.archives import MAX_PICTURES, ArchiveError, Skipped, collect_pictures
from app.intake.images import ACCEPT, FORMATS, shrink_to_jpeg
from app.intake.matching import match_rows
from app.intake.spreadsheet import (
    HEADINGS,
    ApplicationRow,
    SpreadsheetError,
    SpreadsheetFile,
    choose_spreadsheet,
    read_spreadsheet,
)
from app.limits import Limits, RequestSizeLimit, SecurityHeaders, how_long, visitor_id
from app.presenting import (
    BEVERAGE_CHOICES,
    TEXT_FIELDS,
    batch_view,
    data_uri,
    picture_views,
    results_view,
)
from app.reading.ocr import tesseract_available
from app.reading.providers import HedgedReader, make_reader
from app.rules.application import Application, BeverageType
from app.samples import SampleLabel, featured, pictures, sample_files_zip, sample_labels

HERE = Path(__file__).resolve().parent
PREVIEW_EDGE = 900

# Logs carry error kinds, status codes, and request IDs only. Never pictures or label text.
log = logging.getLogger("ttb_label_verifier")

settings = load_settings()

# Uploads must stay in memory. Starlette writes any uploaded file larger than
# spool_max_size to a temporary file on disk, so raise it above the largest
# request the size limit lets through.
MultiPartParser.spool_max_size = settings.max_request_bytes + 1

# The interactive API docs load scripts from an outside CDN, so they stay off.
app = FastAPI(title="TTB Label Verifier", docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(SecurityHeaders)
app.add_middleware(RequestSizeLimit, max_bytes=settings.max_request_bytes)
app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
app.state.limits = Limits.from_settings(settings)
app.state.batches = BatchStore(settings.batch_keep_seconds)
app.state.batch_concurrency = settings.batch_concurrency
app.state.hedge_after = settings.hedge_after_seconds
app.state.max_waiting_bytes = settings.max_waiting_bytes
app.state.one_batch_at_a_time = asyncio.Semaphore(1)
templates = Jinja2Templates(directory=HERE / "templates")


def get_reader() -> LabelReader | None:
    """The AI reader the settings ask for, made once. None means basic text reading only,
    either by setting or because this server has no Anthropic credentials."""
    if not hasattr(app.state, "reader"):
        app.state.reader = make_reader(settings)
    return app.state.reader


def can_read(reader: LabelReader | None) -> bool:
    return reader is not None or (settings.ocr_fallback and tesseract_available())


NOT_SET_UP = "The label reader is not set up on this server. Please tell the administrator."
COULD_NOT_READ = "The label could not be read just now. Please try again in a moment."
NO_SPREADSHEET = "Add the spreadsheet of applications, or put it in the ZIP file with the pictures."


def too_big(size: int, cap: int) -> str:
    return (
        f"The pictures in this batch come to {size / MB:,.0f} MB once unpacked, more than the "
        f"{cap // MB:,} MB the app can hold at once. Please split it into smaller batches."
    )


def busy(seconds: float) -> str:
    return f"The app is busy with other batches. Please try again in {how_long(seconds)}."


def visitor(request: Request) -> str:
    return visitor_id(request.headers, request.client.host if request.client else None)


def page(request: Request, status_code: int = 200, **context) -> HTMLResponse:
    context = {
        "beverage_types": BEVERAGE_CHOICES,
        "text_fields": TEXT_FIELDS,
        "form": {},
        "errors": [],
        "settings": settings,
        "formats": FORMATS,
        "accept": ACCEPT,
        "samples": featured(),
        "sample_count": len(sample_labels()),
        "sample_picture_count": sum(len(label.images) for label in sample_labels().values()),
        **context,
    }
    return templates.TemplateResponse(request, "index.html", context, status_code=status_code)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return page(request)


@app.get("/health")
def health() -> dict[str, str]:
    """Lets Azure confirm the app is running."""
    return {"status": "ok"}


@app.post("/check", response_class=HTMLResponse)
async def check(request: Request, reader: Annotated[LabelReader | None, Depends(get_reader)]):
    try:
        form = await request.form(max_files=settings.max_images_per_label, max_fields=20)
    except HTTPException:
        return page(
            request,
            422,
            errors=[f"Please choose no more than {settings.max_images_per_label} pictures."],
        )

    names = ["beverage_type", *(field.name for field in TEXT_FIELDS)]
    values = {name: str(form.get(name) or "").strip() for name in names}
    uploads = [f for f in form.getlist("images") if isinstance(f, UploadFile) and f.filename]

    errors = []
    try:
        beverage_type = BeverageType(values["beverage_type"])
    except ValueError:
        errors.append("Choose the type of product.")
    for field in TEXT_FIELDS:
        if field.required and not values[field.name]:
            errors.append(f"Fill in the {field.label.lower()}.")
    if not uploads:
        errors.append("Add at least one picture of the label.")
    max_mb = settings.max_image_bytes // (1024 * 1024)
    for upload in uploads:
        if (upload.size or 0) > settings.max_image_bytes:
            errors.append(f'"{upload.filename}" is larger than {max_mb} MB.')
    if not can_read(reader):
        errors.append(NOT_SET_UP)
    if errors:
        if uploads:
            errors.append(
                "For your safety the pictures were not kept, so please choose them again."
            )
        await form.close()
        return page(request, 422, errors=errors, form=values)

    images = [(upload.filename or "picture", await upload.read()) for upload in uploads]
    await form.close()
    application = Application(beverage_type, **{f.name: values[f.name] for f in TEXT_FIELDS})
    return await single_check(request, reader, application, images, values)


async def single_check(
    request: Request,
    reader: LabelReader | None,
    application: Application,
    images: list[tuple[str, bytes]],
    values: dict[str, str],
    sample: SampleLabel | None = None,
) -> HTMLResponse:
    """Check one label and show the results page. Shared by uploads and sample buttons."""
    # Count the check only now, when it will really reach the reader.
    refusal = request.app.state.limits.take_check(visitor(request))
    if refusal:
        return page(request, 429, errors=[refusal], form=values)
    if reader is not None:
        reader = HedgedReader(reader, request.app.state.hedge_after)
    try:
        outcome = await check_one(
            application,
            images,
            reader,
            settings.max_image_edge,
            settings.ocr_fallback,
            outline=True,
        )
    except NotAnImage as error:
        return page(
            request,
            422,
            errors=[f"{error} Please choose a picture or PDF ({FORMATS})."],
            form=values,
        )
    except TooManyPictures as error:
        return page(request, 422, errors=[str(error)], form=values)
    except NoReader:
        return page(request, 503, errors=[COULD_NOT_READ], form=values)

    previews = [
        data_uri(await asyncio.to_thread(shrink_to_jpeg, image, PREVIEW_EDGE))
        for image in outcome.images
    ]
    return page(
        request,
        outcome=outcome,
        pictures=picture_views(outcome, previews),
        sample=sample,
        **results_view(outcome),
    )


TEMPLATE_ROWS = [
    list(HEADINGS),
    [
        "old-tom-front.jpg; old-tom-back.jpg",
        "Distilled spirits",
        "OLD TOM DISTILLERY",
        "Kentucky Straight Bourbon Whiskey",
        "45% Alc./Vol. (90 Proof)",
        "750 mL",
        "Old Tom Distillery, Bardstown, Kentucky",
        "",
    ],
    [
        "landrevin.jpg",
        "Wine",
        "Chateau Landrevin",
        "Bordeaux Red Wine",
        "Alcohol 13.5% by volume",
        "750 mL",
        "Landrevin Imports, New York, NY",
        "France",
    ],
]


@app.get("/template.csv")
def spreadsheet_template() -> Response:
    out = io.StringIO()
    csv.writer(out).writerows(TEMPLATE_ROWS)
    return Response(
        out.getvalue(),
        media_type="text/csv",
        headers={"content-disposition": 'attachment; filename="batch-template.csv"'},
    )


@app.post("/batches", response_class=HTMLResponse)
async def start_batch(request: Request, reader: Annotated[LabelReader | None, Depends(get_reader)]):
    try:
        form = await request.form(max_files=settings.max_batch_files, max_fields=10)
    except HTTPException:
        return page(request, 422, errors=[f"Please send no more than {MAX_PICTURES} pictures."])

    sheet = form.get("spreadsheet")
    has_sheet = isinstance(sheet, UploadFile) and bool(sheet.filename)
    uploads = [f for f in form.getlist("pictures") if isinstance(f, UploadFile) and f.filename]
    errors = []
    if not uploads:
        if not has_sheet:  # and no ZIP file it could be in
            errors.append(NO_SPREADSHEET)
        errors.append("Add the label pictures, or a ZIP file of them.")
    if not can_read(reader):
        errors.append(NOT_SET_UP)
    if errors:
        await form.close()
        return page(request, 422, errors=errors)

    note = None
    try:
        # A spreadsheet in its own box is read first, so a mistake in it shows at once.
        added = SpreadsheetFile(sheet.filename, await sheet.read()) if has_sheet else None
        rows = read_spreadsheet(added.name, added.data) if added else None
        files = [(upload.filename, await upload.read()) for upload in uploads]
        await form.close()
        collected = await asyncio.to_thread(collect_pictures, files)
        chosen, note = choose_spreadsheet(added, collected.spreadsheets)
        if chosen is None:
            return page(request, 422, errors=[NO_SPREADSHEET])
        if rows is None:
            rows = read_spreadsheet(chosen.name, chosen.data)
    except (SpreadsheetError, ArchiveError) as error:
        await form.close()
        return page(request, 422, errors=[str(error), *([note] if note else [])])
    del files

    notes = [note] if note else []
    return await start_job(request, reader, rows, collected.pictures, collected.skipped, notes)


async def start_job(
    request: Request,
    reader: LabelReader | None,
    rows: list[ApplicationRow],
    batch_pictures: dict[str, bytes],
    skipped: list[Skipped],
    notes: list[str] | None = None,
):
    """Start a batch and go to its page. Shared by uploads and the sample batch."""
    matched, unused = match_rows(rows, batch_pictures)
    job = new_job(matched, skipped, unused)
    job.notes = notes or []
    if job.work:
        # Pictures wait in memory until their label is checked, so there is a cap on
        # how much all batches together may hold. Checked first, so that a batch turned
        # away doesn't use up the visitor's limits.
        size, cap = sum(picture_sizes(job.work)), request.app.state.max_waiting_bytes
        if size > cap:
            return page(request, 413, errors=[too_big(size, cap)])
        wait = request.app.state.batches.seconds_until_room(size, cap)
        if wait:
            return page(request, 503, errors=[busy(wait)])
        refusal = request.app.state.limits.take_batch(visitor(request), len(job.work))
        if refusal:
            return page(request, 429, errors=[refusal])
    request.app.state.batches.add(job)
    job.task = asyncio.create_task(
        run_job(
            job,
            reader,
            settings.max_image_edge,
            request.app.state.batch_concurrency,
            request.app.state.one_batch_at_a_time,
            ocr_fallback=settings.ocr_fallback,
        )
    )
    return RedirectResponse(f"/batches/{job.id}", status_code=303)


@app.post("/samples/batch", response_class=HTMLResponse)
async def sample_batch(
    request: Request, reader: Annotated[LabelReader | None, Depends(get_reader)]
):
    labels = list(sample_labels().values())
    if not labels:
        return page(request, 404, errors=["The sample labels are not available on this server."])
    if not can_read(reader):
        return page(request, 422, errors=[NOT_SET_UP])
    batch_pictures = {name: data for label in labels for name, data in pictures(label)}
    return await start_job(request, reader, [label.row for label in labels], batch_pictures, [])


@app.get("/samples/files.zip")
async def sample_files(request: Request) -> Response:
    if not sample_labels():
        return page(request, 404, errors=["The sample labels are not available on this server."])
    return Response(
        await asyncio.to_thread(sample_files_zip),
        media_type="application/zip",
        headers={"content-disposition": 'attachment; filename="ttb-sample-labels.zip"'},
    )


@app.post("/samples/{sample_id}/check", response_class=HTMLResponse)
async def sample_check(
    request: Request,
    sample_id: str,
    reader: Annotated[LabelReader | None, Depends(get_reader)],
):
    label = sample_labels().get(sample_id)
    if label is None:
        return page(request, 404, errors=["There is no sample label with that name."])
    if not can_read(reader):
        return page(request, 422, errors=[NOT_SET_UP])
    return await single_check(
        request, reader, label.row.application, pictures(label), {}, sample=label
    )


GONE = (
    "These batch results are no longer available. Results are kept for 30 minutes after "
    "a batch finishes, then deleted."
)


@app.get("/batches/{job_id}", response_class=HTMLResponse)
async def batch_page(request: Request, job_id: str):
    job = request.app.state.batches.get(job_id)
    if job is None:
        return page(request, 404, errors=[GONE])
    return templates.TemplateResponse(request, "batch.html", batch_view(job))


@app.get("/batches/{job_id}/results", response_class=HTMLResponse)
async def batch_results(request: Request, job_id: str):
    """The changing part of the batch page, which the page's script fetches as it updates."""
    job = request.app.state.batches.get(job_id)
    if job is None:
        return HTMLResponse(f"<p>{GONE}</p>", status_code=404)
    return templates.TemplateResponse(request, "_batch_results.html", batch_view(job))


@app.get("/batches/{job_id}/progress")
async def batch_progress(request: Request, job_id: str):
    job = request.app.state.batches.get(job_id)
    if job is None:
        return JSONResponse({"state": "gone"}, status_code=404)
    return {"state": job.state, "done": job.done, "total": job.total}


@app.get("/batches/{job_id}/previews/{row_number}.jpg")
async def batch_preview(request: Request, job_id: str, row_number: int):
    job = request.app.state.batches.get(job_id)
    item = next((i for i in job.items if i.row_number == row_number), None) if job else None
    if item is None or item.preview is None:
        return Response(status_code=404)
    return Response(item.preview, media_type="image/jpeg")


@app.get("/batches/{job_id}/results.xlsx")
async def batch_excel(request: Request, job_id: str):
    job = request.app.state.batches.get(job_id)
    if job is None:
        return page(request, 404, errors=[GONE])
    if job.state != "finished":
        return page(
            request,
            409,
            errors=["The batch is still running. Download the results when it finishes."],
        )
    workbook = await asyncio.to_thread(results_workbook, job)
    day = datetime.now(UTC).strftime("%Y-%m-%d")
    return Response(
        workbook,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"content-disposition": f'attachment; filename="label-results-{day}.xlsx"'},
    )
