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

The latest run, on Oct 19, 2026: in process, with the app's default settings (1568-pixel
pictures, thinking off, low effort) and outlines on, as in a single check. Full results:
[evaluation-2026-10-19-anthropic.md](measurements/evaluation-2026-10-19-anthropic.md).

| Measure | Result |
|---|---|
| False passes | **0** of 217 field results |
| False fails | **0** |
| Field results as expected | 217 of 217, photo-like labels included |
| Clean label fields read exactly as printed | 159 of 161 |
| Time per label (median / p95 / max) | 2.46 s / 2.95 s / 4.15 s |
| Labels checked in under 5 seconds | 31 of 31 |
| Fields to look at that were outlined on the picture | 17 of 22 |
| AI cost for the 31 labels (estimate from tokens) | $0.022, about 0.07 cents a label |

The two clean fields not read exactly didn't change any result:

- On the label whose warning heading is not bold, Claude said it couldn't tell whether the
  heading was bold, rather than "no". The rule treats anything short of a clear yes as
  Check this, which is the expected result.
- On the French wine, Claude copied both "Mis en bouteille au château" and the "Imported by"
  statement, as its instructions now say. The answer key lists only the importer statement.

The 5 fields not outlined are the brand in Japanese script, which Tesseract can't read in
English mode, and fields on four of the hard photos (blurry, glare, and tilted). Those still
get their result; only the outline is missing.

### Found and fixed by the evaluation

The run before this one had **one false fail**. On the French wine, Claude reported only "Mis
en bouteille au château", in larger type, as the bottler statement, because the instructions
said to report the most prominent one. The importer check then failed against "Landrevin
Imports, New York, NY". An earlier run that morning had read both lines and passed, but only
by luck: the rule could skip at most six words before "Imported by".

The fix (commit `2725363`) changed both sides. The reader now copies every statement that names
a company. The rule splits the text into its statements and passes if any one matches the
application. In 5 runs of that sample with real Claude, all 5 read the importer statement
and passed. The run with the false fail is kept in the git history (commit `fa442c7`).

On the blurry photo of the label with words missing from the warning, earlier runs marked the
warning unclear, so it came out as Check this instead of Problem. That is an acceptable
answer on a hard photo: the agent is sent to look.

### Speed varies between runs

Four full runs were made on Oct 19. The first, on the first 19 labels, had 2 labels over 5
seconds (5.4 s and 6.2 s), with the same number of tokens as the fast ones. That points to
variation on the API's side, not the labels. The three runs on all 31 labels had none over
5 seconds; their slowest labels took 4.21 s, 3.36 s, and 4.15 s. Outlines didn't add
measurably to the time, because Tesseract finds the words while Claude reads: the median
was 2.38 s without them, and 2.39 s and 2.46 s with them. Every run is kept in the git
history (`093322d`, `7f94e72`, `fa442c7`, `dbc98dc`).

If slow answers come back, one option is to send the same request a second time when the
first hasn't answered within about 3.5 seconds, and use whichever answer arrives first. It
would add roughly a cent per hundred labels. It is not built.

## On the live app, end to end

The same 31 labels were sent to the deployed app through its web pages
(`tools/evaluate.py --url`), on Oct 19 with the API key set. Each label was checked once on
its own, as an agent would, and once more in a batch of all 31. Full results:
[evaluation-2026-10-19-deployed.md](measurements/evaluation-2026-10-19-deployed.md).
More timing, with phone-sized photos and after a cold start:
[live-single-check-2026-10-19.md](measurements/live-single-check-2026-10-19.md).

| Measure | Result |
|---|---|
| Read by Claude | 31 of 31, on their own and in the batch |
| False passes / false fails | **0** / **0** |
| Field results as expected (from the batch) | 217 of 217 |
| Single check, end to end (median / p95 / max) | 2.95 s / 4.65 s / 8.79 s |
| Of that, inside the app | 2.8 s / 4.5 s / 8.6 s |
| Single checks done in under 5 seconds | 30 of 31 |
| Fields to look at that were outlined | 17 of 22, the same fields as in process |
| Batch of 31 labels, upload to finished | 16.1 s |
| Phone-sized photo (6 MB JPEG), end to end (median of 5) | 3.47 s |
| Two phone-sized photos (12 MB), end to end (median of 3) | 4.17 s |
| First check after the app scaled to zero | 26.6 s, of which 3.4 s was the check |

End to end includes the outline wait: a check waits at most 1 second for the outlines
once Claude has answered. The app's logs show the wait never reached that limit. The one
check over 5 seconds was a slow answer from the API, like the ones seen in process. A big
photo adds its upload time (about 0.8 s for 6 MB on a home connection) but nothing inside
the app, because every picture is shrunk before Claude sees it.

The slow first check is Azure starting the app after it has scaled to zero: pulling the
image, creating the container, starting it, and a health probe. It happens after about 5
minutes without requests. Keeping one replica running would remove it; that's an open cost
decision.

## Results with basic text reading (offline)

The same 31 labels, read with Tesseract OCR only, as when Claude can't be reached. Full
results: [evaluation-2026-10-19-ocr.md](measurements/evaluation-2026-10-19-ocr.md).

| Measure | Result |
|---|---|
| False passes | **0** |
| False fails | **0** |
| Clean labels with every field as expected | 1 of 23 |
| Field results: exact / extra review / review instead of fail | 158 / 43 / 16 |
| Time per label (median / max), outlines included | 0.45 s / 0.8 s |
| Fields to look at that were outlined on the picture | 44 of 44 |

This is what the offline mode is designed to do: it never marks a Problem, and it sends
anything it can't confirm to Check this. It is a safety net, not a replacement for Claude.
Every field it flags is outlined, because it only ever finds text that Tesseract can see.
These times are on a laptop; on the app's one Azure CPU, basic text reading is slower.

## Limits of this evaluation

- **The labels are drawn by code,** by the same project that wrote the rules. Real labels
  have curved bottles, foil, embossing, script fonts, and busy artwork.
- **The photo-like labels are simulated** (rotated, skewed, blurred, darkened, with a glare
  spot), not taken with a camera.
- **The set is small.** No false passes in 217 field results is encouraging, but it does not
  prove the rate is zero.
- **Each label was read once per run.** Claude's times vary from run to run.
- **The live runs were from one home connection,** one check at a time. An agency network,
  or many agents at once, would give different times.

## Run it again

```sh
uv run --env-file .env python -m tools.evaluate            # Claude, in this process
uv run python -m tools.evaluate --reader ocr               # offline reader only, no cost
uv run python -m tools.evaluate --url https://... --deployed-as "revision ..., image ..."
uv run python -m tools.time_live --url https://... --phone  # phone-sized photos, timed
uv run python -m tools.evaluate --only old-tom-bourbon     # some labels only
```

Each run with Claude costs about two cents; against a deployed app, about four, because each
label is read twice. Results are saved to `docs/measurements/` as JSON and Markdown, exactly
as measured.
