# Evaluation

How well the app reads and judges labels, and how fast. Every number here comes from a run
recorded in [docs/measurements](measurements), and can be repeated with `tools/evaluate.py`.

## What matters most

The worst mistake is a **false pass**: a label with a real problem shown as **Matches**. An
agent who trusts it lets a bad label through. A **false fail** (a **Problem** on a field that
is fine) wastes an agent's time and erodes trust. **Check this** on a hard-to-read photo is
the honest answer, and is fine.

The other goal is speed: the interviews asked for a result in about 5 seconds.

## The test labels

There are 31 labels in `samples/`, drawn by `tools/make_samples.py` with made-up brands:

- **23 clean labels.** Three have nothing wrong. The others each plant one or more known
  problems, covering every rule:
  - Mismatches: alcohol content, net contents, proof that doesn't fit the ABV.
  - Names: brand in capitals, accents, a brand in Japanese script against a romanized
    application.
  - Countries written in other languages ("Produkt aus Deutschland", "Hecho en México").
  - The warning: wrong wording, heading not in capitals, heading not bold, warning missing.
  - TTB rules: proof without a percentage, centiliters on spirits, metric-only beer, a bottle
    size that isn't allowed, dessert wine without an alcohol statement, table wine allowed
    to leave it out, brand and alcohol on different sides, no "Bottled by".
  - A label that tries to trick the AI (prompt injection), with a real alcohol error next to it.
- **8 photo-like versions** of clean labels: tilted, at an angle, blurry, dim, with glare, and
  from far away.

`samples/expected.json` holds the expected result for every field of every label (217 field
results in all), and what was planted, in plain words. It was written when the samples were
drawn, before any evaluation ran.

### How each field is judged

| Judgment | Meaning |
|---|---|
| exact | the expected result |
| false pass | a planted problem shown as Matches |
| false fail | a Problem where none was planted (or only Check this was expected) |
| review instead of fail | a planted problem shown as Check this rather than Problem |
| extra review | Check this on a field that is fine |

On clean labels, only "exact" counts as right. On photo-like labels, Check this is also
acceptable, because the photo really is harder to read.

## Results with Claude Haiku 5.5

Run on Oct 19, 2026, in process, with the app's default settings (1568-pixel pictures,
thinking off, low effort). Full results: [evaluation-2026-10-19-anthropic.md](measurements/evaluation-2026-10-19-anthropic.md).

| Measure | Result |
|---|---|
| False passes | **0** of 217 field results |
| False fails | **0** |
| Clean labels with every field as expected | 23 of 23 |
| Photo-like label fields with an acceptable result | 56 of 56 |
| Clean label fields read exactly as printed | 159 of 161 |
| Time per label (median / p95 / max) | 2.38 s / 3.39 s / 4.21 s |
| Labels checked in under 5 seconds | 31 of 31 |
| AI cost for the 31 labels (estimate from tokens) | $0.022, about 0.07 cents a label |

What wasn't perfect:

- **The blurry warning.** On the blurry photo of the label with words missing from the
  warning, Claude marked the warning unclear, so the result was Check this instead of
  Problem. That is the acceptable outcome: the agent is sent to look.
- **Two clean fields not read exactly:**
  - On the label whose warning heading is not bold, Claude said it couldn't tell whether the
    heading was bold, rather than "no". The rule treats anything short of a clear yes as
    Check this, so the result was still as expected.
  - On the French wine, Claude included the French phrase "Mis en bouteille au château" in
    the importer statement. The importer still matched.

### Speed varies between runs

An earlier run the same morning, on the first 19 labels, had 2 labels over 5 seconds
(5.4 s and 6.2 s), with the same number of tokens as the fast ones. That points to variation
on the API's side, not the labels. The second run, on all 31 labels, had none over 5
seconds. The first run is kept in the git history (commit `093322d`).

If slow answers come back, one option is to send the same request a second time when the
first hasn't answered within about 3.5 seconds, and use whichever answer arrives first. It
would add roughly a cent per hundred labels. It is not built.

## Results with basic text reading (offline)

The same 31 labels, read with Tesseract OCR only, as when Claude can't be reached. Full
results: [evaluation-2026-10-19-ocr.md](measurements/evaluation-2026-10-19-ocr.md).

| Measure | Result |
|---|---|
| False passes | **0** |
| False fails | **0** |
| Clean labels with every field as expected | 1 of 23 |
| Field results: exact / extra review / review instead of fail | 158 / 43 / 16 |
| Time per label (median / max) | 0.25 s / 0.45 s |

This is what the offline mode is designed to do: it never marks a Problem, and it sends
anything it can't confirm to Check this. It is a safety net, not a replacement for Claude.

## Limits of this evaluation

- **The labels are drawn by code,** by the same project that wrote the rules. Real labels
  have curved bottles, foil, embossing, script fonts, and busy artwork.
- **The photo-like labels are simulated** (rotated, skewed, blurred, darkened, with a glare
  spot), not taken with a camera.
- **The set is small.** No false passes in 217 field results is encouraging, but it does not
  prove the rate is zero.
- **Each label was read once per run.** Claude's times vary from run to run.
- **These runs were in process.** They leave out uploading the pictures and loading the page.
  The same script can test the deployed app end to end (`--url`); that run waits until the
  API key is set on Azure.

## Run it again

```sh
uv run --env-file .env python -m tools.evaluate            # Claude, in this process
uv run python -m tools.evaluate --reader ocr               # offline reader only, no cost
uv run python -m tools.evaluate --url https://...          # a deployed app, end to end
uv run python -m tools.evaluate --only old-tom-bourbon     # some labels only
```

Each run with Claude costs about two cents. Results are saved to `docs/measurements/` as JSON
and Markdown, exactly as measured.
