# TTB Label Verifier

Checks alcohol label images against their application data and TTB labeling rules.

A compliance agent adds a label's pictures and what the application says, or a whole batch
as a spreadsheet plus a ZIP of pictures. The app reads each label and shows, field by
field, whether it matches the application and follows the basic TTB rules: **Matches**,
**Check this**, or **Problem**, each with one plain sentence saying why.

**Live prototype:** https://ttb-label-verifier.kindmoss-39b6eae5.eastus2.azurecontainerapps.io

Prototype. Not an official TTB or U.S. government website.

## Status

In development (October 2026). These work and are deployed:

- single-label and batch checks, with an Excel download of batch results
- sample labels to try with one click
- drag and drop, and JPEG, PNG, WebP, GIF, HEIC, TIFF, and PDF pictures, alone or in ZIP or
  7z files
- each field to look at outlined on the label picture
- tips for taking a better photo
- the offline fallback
- a second request to Claude when a single check's answer is slow

The evaluation has been run on the deployed app as well as in process: every sample label
was read by Claude on the live app, and every field result was as expected (see
[Accuracy and speed](#accuracy-and-speed)).

Claude in Microsoft Foundry is built and tested offline. On Azure, the Foundry resource and
keyless sign-in work, but the model deployment waits on quota.

## How it decides

**AI reads, code decides.** Claude only reads the label and returns what is printed, field
by field, as JSON. It never sees the application, and its output has no place for a verdict.
Ordinary, tested Python code compares the reading with the application and applies the TTB
rules. Every TTB check cites the eCFR paragraph it comes from.

See [docs/APPROACH.md](docs/APPROACH.md) for the approach, the rules, the assumptions, and the
limits, and [docs/ACCESSIBILITY.md](docs/ACCESSIBILITY.md) for how the pages are made easy to
use and what was checked.

## Accuracy and speed

On 31 sample labels (23 clean, 8 made to look like poor photos), with Claude Haiku 5.5:

- **Every field result was as expected,** 217 of 217: no planted problem was shown as
  Matches, and no fine field was shown as a Problem.
- **Every label was checked in under 5 seconds** in process (median 2.5 s, slowest 4.2 s). On
  the live app, end to end from a home connection, the median was 2.95 s and 30 of 31 were
  under 5 seconds; one slow answer from the API took 8.8 s.
- **The first check after a quiet spell** waits about 23 seconds more, while Azure starts the
  app. It scales to zero after 5 minutes without requests.
- **The AI cost** was about 0.07 cents a label.

An earlier run found one false Problem, on a French wine's importer statement. It was fixed
and checked again. The labels are drawn by code, so this is a first measure, not proof. See
[docs/EVALUATION.md](docs/EVALUATION.md) for the method, the details, and the limits.

## Run locally

Requires Python 3.12, [uv](https://docs.astral.sh/uv/), and Tesseract, for the outlines and
the offline fallback (`brew install tesseract` on macOS, `apt-get install tesseract-ocr` on
Debian or Ubuntu). Without Tesseract the app still runs and Claude still reads the labels,
but no fields are outlined on the pictures, and if Claude can't be reached, labels can't be
checked at all.

```sh
cp .env.example .env      # then put your Anthropic API key in .env
uv sync
uv run --env-file .env uvicorn app.main:app --reload
```

Then open http://127.0.0.1:8000. Without an API key the app still runs, using basic text
reading (OCR) only.

To try a batch, use "Try a sample batch", or upload `samples/applications.csv` and the
pictures in `samples/labels/`. On the home page, "Download the sample files" gives the same
files as one ZIP.

## Settings

All settings come from environment variables. See [.env.example](.env.example).

| Variable | Default | Meaning |
|---|---|---|
| `ANTHROPIC_API_KEY` | none | Key for the Claude API. In Azure it comes from a secret. |
| `TTB_READER` | `anthropic` | `anthropic` (Claude through the Anthropic API), `foundry` (Claude in Microsoft Foundry, in Azure), or `ocr` (basic text reading only) |
| `TTB_FOUNDRY_RESOURCE` | none | The Foundry resource name, for `TTB_READER=foundry`. In Azure the app signs in with its managed identity; no key is stored. |
| `TTB_LABELS_PER_MINUTE` | `0` | Pace calls to the AI reader to stay inside a quota (`0` means no pacing) |
| `TTB_BATCH_CONCURRENCY` | `8` | Labels read at the same time within a batch |
| `TTB_OCR_FALLBACK` | `on` | Use basic text reading when Claude can't be reached |
| `TTB_CLAUDE_MODEL` | `claude-haiku-5-5` | Claude model |
| `TTB_CLAUDE_THINKING` | `off` (`adaptive` for Foundry) | `off` or `adaptive`. Foundry needs `adaptive`. |
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
and writes `samples/applications.csv` and `samples/expected.json`. There are 23 labels, each
with known planted errors and the expected result for every field, plus 8 photo-like
versions (tilted, blurry, dim, glare, and so on). One label carries a prompt-injection
attempt. Regenerate with `uv run python -m tools.make_samples`. Sample labels are for
evaluation; a production version would remove them.

`tools/evaluate.py` checks every sample and records accuracy, speed, and cost in
`docs/measurements/`, in process or against the deployed app. `tools/time_live.py` times
single checks on the deployed app, with phone-sized photos if asked. See
[docs/EVALUATION.md](docs/EVALUATION.md).

## Project layout

```
app/
  main.py          web routes
  checking.py      check one label: prepare pictures, read, apply rules
  batch.py         background batch jobs, kept in memory
  export.py        Excel results, built in memory
  limits.py        upload size limit, security headers, usage limits
  presenting.py    results in plain words, for the pages
  highlights.py    where each field to look at is on the label picture
  photo_coach.py   tips for a better photo
  samples.py       the sample labels behind "Try a sample"
  intake/          pictures, ZIP and 7z files, spreadsheets, matching rows to pictures
  reading/         the JSON contract, the Claude reader, and the OCR fallback
  rules/           every matching and TTB rule, with eCFR citations
  templates/, static/
tools/             sample label generator, evaluation, and timing scripts
samples/           sample labels, applications, expected results
tests/
docs/              approach, evaluation, accessibility, deployment, measurements
```

## Deployment

The app runs as one container on Azure Container Apps. See [docs/DEPLOY.md](docs/DEPLOY.md).

## Tools used to build this project

- [Claude Code](https://claude.com/claude-code) (Anthropic), an AI coding assistant, used under
  Christopher Parker's direction for planning, research, code, and tests.
- Claude Haiku 5.5 reads the labels, through the Anthropic Python SDK (or Microsoft Foundry,
  signing in with azure-identity).
- Tesseract OCR finds where words are on a label, for the outlines, and is the offline
  fallback reader.
- Python 3.12, FastAPI, Jinja2, Pillow, pillow-heif (HEIC), pypdfium2 (PDF), py7zr (7z),
  openpyxl (reading spreadsheets), XlsxWriter (writing results), pytest, ruff, and uv.
- Azure Container Apps and Azure Container Registry host the prototype.
