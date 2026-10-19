"""Web entry point for the TTB Label Verifier."""

import asyncio
import base64
import logging
from pathlib import Path
from typing import Annotated

import anthropic
from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.datastructures import UploadFile
from starlette.exceptions import HTTPException
from starlette.formparsers import MultiPartParser

from app.checking import LabelReader, NotAnImage, check_one
from app.config import load_settings
from app.intake.images import shrink_to_jpeg
from app.limits import Limits, RequestSizeLimit, SecurityHeaders, visitor_id
from app.presenting import BEVERAGE_CHOICES, TEXT_FIELDS, results_view
from app.reading.claude import ClaudeReader, ReadingFailed
from app.rules.application import Application, BeverageType

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
app.state.limits = Limits(
    settings.checks_per_visitor,
    settings.check_window_seconds,
    settings.batches_per_visitor,
    settings.batch_window_seconds,
    settings.labels_per_day,
)
templates = Jinja2Templates(directory=HERE / "templates")


def get_reader() -> LabelReader | None:
    """The Claude reader, or None if this server has no Anthropic credentials."""
    if not hasattr(app.state, "reader"):
        try:
            client = anthropic.AsyncAnthropic(max_retries=1, timeout=30)
        except anthropic.AnthropicError:
            return None
        app.state.reader = ClaudeReader(
            client, thinking=settings.thinking, effort=settings.effort, model=settings.model
        )
    return app.state.reader


def page(request: Request, status_code: int = 200, **context) -> HTMLResponse:
    context = {
        "beverage_types": BEVERAGE_CHOICES,
        "text_fields": TEXT_FIELDS,
        "form": {},
        "errors": [],
        "settings": settings,
        **context,
    }
    return templates.TemplateResponse(request, "index.html", context, status_code=status_code)


def data_uri(jpeg: bytes) -> str:
    return "data:image/jpeg;base64," + base64.b64encode(jpeg).decode("ascii")


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
    if reader is None:
        errors.append(
            "The label reader is not set up on this server. Please tell the administrator."
        )
    if errors:
        if uploads:
            errors.append(
                "For your safety the pictures were not kept, so please choose them again."
            )
        await form.close()
        return page(request, 422, errors=errors, form=values)

    # Count the check only now, when it will really reach the reader.
    visitor = visitor_id(request.headers, request.client.host if request.client else None)
    refusal = request.app.state.limits.take_check(visitor)
    if refusal:
        await form.close()
        return page(request, 429, errors=[refusal], form=values)

    images = [(upload.filename or "picture", await upload.read()) for upload in uploads]
    await form.close()
    application = Application(beverage_type, **{f.name: values[f.name] for f in TEXT_FIELDS})

    try:
        outcome = await check_one(application, images, reader, settings.max_image_edge)
    except NotAnImage as error:
        return page(
            request,
            422,
            errors=[f"{error} Please choose a JPEG, PNG, WebP, or GIF picture."],
            form=values,
        )
    except (ReadingFailed, anthropic.APIError) as error:
        log.warning(
            "Label reading failed: %s status=%s request_id=%s",
            type(error).__name__,
            getattr(error, "status_code", None),
            getattr(error, "request_id", None),
        )
        return page(
            request,
            503,
            errors=["The label reader could not read this label just now. Please try again."],
            form=values,
        )

    previews = [
        data_uri(await asyncio.to_thread(shrink_to_jpeg, image, PREVIEW_EDGE))
        for image in outcome.images
    ]
    return page(request, outcome=outcome, previews=previews, **results_view(outcome))
