# TTB Label Verifier

Checks alcohol label pictures against their application data and basic TTB labeling rules. An
agent adds a label's pictures and what the application says, or a whole batch as a spreadsheet
plus pictures, and sees each field as **Matches**, **Check this**, or **Problem**, with one plain
sentence saying why.

**Demo:** https://ttb-label-verifier.kindmoss-39b6eae5.eastus2.azurecontainerapps.io (press a
sample button; the first check after a quiet spell takes about 25 seconds more while Azure
starts the app)

Prototype. Not an official TTB or U.S. government website.

## Quick start

Needs Python 3.12, [uv](https://docs.astral.sh/uv/), and Tesseract (`brew install tesseract`,
or `apt-get install tesseract-ocr`).

```sh
cp .env.example .env      # then put an Anthropic API key in .env
uv sync
uv run --env-file .env uvicorn app.main:app --reload    # open http://127.0.0.1:8000
uv run pytest                                           # no network or API key needed
```

Without a key, the app reads labels with basic text reading (Tesseract) only.

## How it decides

**AI reads, code decides.** Claude Haiku 5.5 only reads the label into JSON. It never sees the
application, and its answer has no place for a verdict. Tested Python code compares the reading
with the application and applies the TTB rules, each citing its eCFR paragraph. Where a reading
is uncertain or a rule needs judgment, the answer is Check this, not Problem. In single checks,
some fields to look at are also outlined on the picture. See [APPROACH](docs/APPROACH.md).

## Requirements, by stakeholder

| Who | Asked for | Status |
|---|---|---|
| Sarah Chen | Results in about 5 seconds | Met: live single checks, median 2.9 s, 31 of 31 under 5 s |
| Sarah Chen | Simple enough for anyone | Built for it: large type, plain words, one main button. Checked by hand by keyboard alone and with VoiceOver ([ACCESSIBILITY](docs/ACCESSIBILITY.md)) |
| Sarah Chen, Janet | Batches of 200 to 300 labels | Met: a spreadsheet plus pictures, loose or zipped; 300 labels in about 4.5 minutes |
| Marcus Williams | Standalone, on Azure, nothing sensitive stored | Met: one container. This app keeps pictures in memory only, and deletes batch results after 30 minutes |
| Marcus Williams | Firewall blocks outside AI services | Partly: if the AI provider is blocked, a check falls back to offline OCR within about 8.5 s, giving Check this at most. Claude in Microsoft Foundry is optional, not yet validated |
| Dave Morrison | Judgment ("STONE'S THROW" is "Stone's Throw") | Met for capitals, punctuation, company forms, and state names |
| Dave Morrison | Don't make my life harder | Partly: 11 false Problems on 24 real labels (fourth set), 5 of them where the registry's brand isn't the label's |
| Jenny Park | Warning word for word; heading in capitals and bold | Wording and capitals checked; bold is judged by the AI and can be wrong |
| Jenny Park | Imperfect photos | Partly: simulated poor photos give acceptable results, with photo tips; real camera photos are untested |

## Latest results

- **31 sample labels**, code-drawn, in process (commit `2ebfda9`): no false Problems; 1 false
  pass, a warning heading that isn't bold read as bold (about 1 time in 5); 31 of 31 under 5
  seconds.
- **24 real approved labels** from TTB's Public COLA Registry, a fourth set chosen after the
  last rule changes, the honest measure (commit `6530f56`): 252 of 274 strict field results and
  50 of 62 judgment calls as expected; 24 of 24 planted problems detected; 1 false pass (an
  alcohol statement with a decimal comma, "5,8 %"); 11 false Problems; 44 of 48 checks under 5
  seconds.
- **Live app** (commit `77dd73a`, 2 CPUs): single checks median 2.9 s, 31 of 31 under 5 s;
  a batch of 300 labels in 4.1 to 4.5 minutes, 294 and 297 of 300 rows as expected (the second
  run's misses: that bold heading twice, a bottler once; the first run didn't record which).
- **Cost**: about 0.08 cents a label.

History, method, and limits: [EVALUATION](docs/EVALUATION.md).

## Batches and large photos

A batch upload can be up to 200 MB, with up to 300 applications. Every picture is shrunk to
1568 pixels before reading, so large phone photos work, but they fill the 200 MB quickly: at
4 MB each, about 50 fit. Resize photos to about 1600 pixels on the long side first (nothing
is lost, and about 600 then fit), or split the batch.

## Limitations

- Bold type is judged by the AI from the picture, and can be wrong.
- The warning's second reading, by Tesseract, is missing on more than half of real labels.
- Real labels were tested as the artwork sent to TTB, not as photos of bottles.
- Not checked: type size, contrast, standards of identity, required disclosures.
- One instance: batch jobs and usage limits live in memory and are lost if the app restarts.
- The sets are small: 31 code-drawn labels and four sets of 24 real ones.

Settings and deployment: [DEPLOY](docs/DEPLOY.md).

## Tools used

- [Claude Code](https://claude.com/claude-code) (Anthropic), an AI coding assistant, used under
  Christopher Parker's direction for planning, research, code, and tests. ChatGPT (OpenAI)
  reviewed the project and suggested changes.
- Claude Haiku 5.5 reads the labels, through the Anthropic Python SDK (or Microsoft Foundry,
  signing in with azure-identity).
- Tesseract OCR: outlines, the warning's second reading, and the offline fallback.
- Python 3.12, FastAPI, Jinja2, Pillow, pillow-heif, pypdfium2, py7zr, openpyxl, XlsxWriter,
  pytest, ruff, and uv.
- Azure Container Apps and Azure Container Registry host the prototype.
