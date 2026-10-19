# TTB Label Verifier

Checks alcohol label images against their application data and TTB labeling rules.

A compliance agent adds a label's pictures and what the application says, or a whole batch
as a spreadsheet plus a ZIP of pictures. The app reads each label and shows, field by
field, whether it matches the application and follows the basic TTB rules: **Matches**,
**Check this**, or **Problem**, each with one plain sentence saying why.

**Live prototype:** https://ttb-label-verifier.kindmoss-39b6eae5.eastus2.azurecontainerapps.io

## Status

In development (October 2026). Single-label checks, batch checks, the Excel download, and
the offline fallback work and are deployed. Still to come: the full accuracy and speed
evaluation on harder photos, more picture formats (HEIC, TIFF, PDF), and Claude in Microsoft
Foundry as a second AI provider.

## How it decides

**AI reads, code decides.** Claude only reads the label and returns what is printed, field
by field, as JSON. It never sees the application, and its output has no place for a verdict.
Ordinary, tested Python code compares the reading with the application and applies the TTB
rules. Every TTB check cites the eCFR paragraph it comes from.

See [docs/APPROACH.md](docs/APPROACH.md) for the approach, the rules, the assumptions, and the
limits.

## Run locally

Requires Python 3.12, [uv](https://docs.astral.sh/uv/), and Tesseract for the offline fallback
(`brew install tesseract` on macOS, `apt-get install tesseract-ocr` on Debian or Ubuntu).

```sh
cp .env.example .env      # then put your Anthropic API key in .env
uv sync
uv run --env-file .env uvicorn app.main:app --reload
```

Then open http://127.0.0.1:8000. Without an API key the app still runs, using basic text
reading (OCR) only.

To try a batch, upload `samples/applications.csv` and the pictures in `samples/labels/`.

## Settings

All settings come from environment variables. See [.env.example](.env.example).

| Variable | Default | Meaning |
|---|---|---|
| `ANTHROPIC_API_KEY` | none | Key for the Claude API. In Azure it comes from a secret. |
| `TTB_READER` | `anthropic` | `anthropic` (Claude), or `ocr` for basic text reading only |
| `TTB_OCR_FALLBACK` | `on` | Use basic text reading when Claude can't be reached |
| `TTB_CLAUDE_MODEL` | `claude-haiku-5-5` | Claude model |
| `TTB_CLAUDE_THINKING` | `off` | `off` or `adaptive` |
| `TTB_CLAUDE_EFFORT` | `low` | `low`, `medium`, or `high` (higher needs thinking on) |
| `TTB_MAX_IMAGE_EDGE` | `1568` | Longest side, in pixels, of pictures sent to Claude |

The model, thinking, and image size defaults were picked from a timing test, recorded in
[docs/measurements](docs/measurements).

## Run the checks

```sh
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

The tests need no network and no API key. Where Claude would be called, they use readings
recorded from real runs or built from the sample labels' printed text. Tests that run
Tesseract are skipped if it isn't installed. CI installs it, so they run there.

## Sample labels

`tools/make_samples.py` draws the sample labels in `samples/labels/`, with made-up brands,
and writes `samples/applications.csv` and `samples/expected.json`. Each sample has known
planted errors and the expected result for every field. One label carries a prompt-injection
attempt. Regenerate with `uv run python -m tools.make_samples`.

## Project layout

```
app/
  main.py          web routes
  checking.py      check one label: prepare pictures, read, apply rules
  batch.py         background batch jobs, kept in memory
  export.py        Excel results, built in memory
  limits.py        upload size limit, security headers, usage limits
  intake/          pictures, ZIP files, spreadsheets, matching rows to pictures
  reading/         the JSON contract, the Claude reader, and the OCR fallback
  rules/           every matching and TTB rule, with eCFR citations
  templates/, static/
tools/             sample label generator and timing script
samples/           sample labels, applications, expected results
tests/
docs/              approach, deployment, measurements
```

## Deployment

The app runs as one container on Azure Container Apps. See [docs/DEPLOY.md](docs/DEPLOY.md).

## Tools used to build this project

- [Claude Code](https://claude.com/claude-code) (Anthropic), an AI coding assistant, used under
  Christopher Parker's direction for planning, research, code, and tests.
- Claude Haiku 5.5 through the Anthropic API reads the labels.
- Tesseract OCR is the offline fallback reader.
- Python 3.12, FastAPI, Jinja2, Pillow, openpyxl (reading spreadsheets), XlsxWriter (writing
  results), pytest, ruff, and uv.
- Azure Container Apps and Azure Container Registry host the prototype.
