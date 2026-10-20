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

The latest run, on Oct 20, 2026, after the rules were changed for real labels (see below): in
process, with the app's default settings (1568-pixel pictures, thinking off, low effort) and
outlines on, as in a single check. Full results:
[evaluation-2026-10-20-anthropic.md](measurements/evaluation-2026-10-20-anthropic.md).

| Measure | Result |
|---|---|
| False passes | **0** of 217 field results |
| False fails | **0** |
| Field results as expected | 216 of 217; the other is Check this on a photo-like label, which is acceptable |
| Clean label fields read exactly as printed | 159 of 161 |
| Time per label (median / p95 / max) | 2.49 s / 3.25 s / 3.97 s |
| Labels checked in under 5 seconds | 31 of 31 |
| Fields to look at that were outlined on the picture | 17 of 23 |
| Checks where Tesseract's second reading was ready in time | 31 of 31 |
| AI cost for the 31 labels (estimate from tokens) | $0.022, about 0.07 cents a label |

The Check this is on the photo taken from far away: Claude marked its warning hard to read.
The Oct 19 run, before the changes, had all 217 as expected
([evaluation-2026-10-19-anthropic.md](measurements/evaluation-2026-10-19-anthropic.md)).

The two clean fields not read exactly didn't change any result:

- On the label whose warning heading is not bold, Claude said it couldn't tell whether the
  heading was bold, rather than "no". The rule treats anything short of a clear yes as
  Check this, which is the expected result.
- On the French wine, Claude copied both "Mis en bouteille au château" and the "Imported by"
  statement, as its instructions now say. The answer key lists only the importer statement.

The 6 fields not outlined are the brand in Japanese script, which Tesseract can't read in
English mode, and fields on five of the hard photos (blurry, glare, tilted, and far away). Those still
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

Since Oct 20, a single check sends the same request a second time when the first hasn't
answered within 4 seconds, and uses whichever answer arrives first. See the live results
below for what it did.

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

### Oct 20: slow answers asked for again

After a single check started asking Claude again when it has no answer after 4 seconds, the
evaluation was run on the live app again (revision 19, image `ee5ecb0`), followed by two more
passes over every sample with `tools/time_live.py --sample all --runs 2`. Details:
[live-single-check-2026-10-20.md](measurements/live-single-check-2026-10-20.md) and
[evaluation-2026-10-20-deployed.md](measurements/evaluation-2026-10-20-deployed.md).

| Single checks, end to end | Oct 19 (31) | Oct 20, evaluation run (31) | Oct 20, all (93) |
|---|---|---|---|
| Median / p95 / slowest | 2.95 s / 4.65 s / 8.79 s | 2.51 s / 4.44 s / 4.62 s | 2.54 s / 3.17 s / 4.62 s |
| Under 5 seconds | 30 of 31 | 31 of 31 | 93 of 93 |
| Asked again | not built | 2 | 2 |

The evaluation run again had every field result as expected (217 of 217), every label read
by Claude, and the batch took 13.7 s.

The better tail is not the second request's doing. It was sent twice in 93 checks, and both
times the first request still answered first (after 4.1 and 4.3 s). Claude was simply
quicker that day: no answer took more than 4.5 s inside the app. The slow answer the second
request is meant for (8.6 s on Oct 19) didn't happen in 93 checks, so how much it helps then
is not yet measured. Its cost was measured: 2 extra requests in 93 checks.

### Oct 20: the changed rules and the warning's second reading

After the rules were changed for real labels and the warning got a second reading by
Tesseract, the evaluation was run on the live app again (revision 21, image `f1cac8c`).
Details: [evaluation-2026-10-20-deployed-2.md](measurements/evaluation-2026-10-20-deployed-2.md).

| Measure | Revision 19 (before) | Revision 21 |
|---|---|---|
| Field results as expected (from the batch) | 217 of 217 | 217 of 217, with the second reading |
| Single check, end to end (median / p95 / max) | 2.51 s / 4.44 s / 4.62 s | 2.7 s / 4.15 s / 4.38 s |
| Single checks done in under 5 seconds | 31 of 31 | 31 of 31 |
| Second reading ready in time (single checks) | not built | 31 of 31 |
| **Batch of 31 labels, upload to finished** | 13.7 s | **53.5 s and 55.7 s** (two batches) |

**Batches are about 4 times slower.** In a batch, Tesseract reads the picture with the warning
after Claude answers, so that batches catch the same warning problems as single checks. With 8
labels read at once and one CPU, that reading queues up: about 1.8 s a label, so a batch of 300
would take about 9 minutes instead of about 2. More CPU would shorten it; that's a cost decision.

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

## Real labels from the COLA Registry

Approved labels from TTB's Public COLA Registry, in two sets of 24 (8 spirits, 8 wine, and 8
malt beverages each, all received in 2026). Each label was checked twice, once as approved and
once with one problem planted in its application data: 48 checks a set, in process, with the
app's default settings. The pictures, application data, answer keys, and per-label results are
kept private and never committed. Only totals and the TTB IDs are published.

- **How they were chosen:** by a rule fixed before looking at any label. For each slot (a
  class/type code, domestic or imported), the first approved label approval with a picture, in
  the registry's own order, one per company. The registry was asked slowly, 3 seconds between
  requests. The second set skipped the first set's labels and companies.
- **The application data:** brand name from the registry, word for word. Bottler or importer:
  the company the registry lists, with its city and state. Country of origin from the registry.
  Class, alcohol content, and net contents were copied from the label, because the registry has
  no such fields.
- **The answer keys** were checked by Christopher against every picture before each set's first
  run. Some answers are judgment calls, where two results are right (Matches or Check this for a
  warning that may be bold, for example). Accuracy is given separately for these, never combined.

### Three runs

The first run showed far too many false Problems, so the rules were changed, using that set's
labels: the **tuning set**. Then a **fresh set** was chosen by the same rule and checked once,
with nothing changed after its labels were seen. **The fresh set is the honest number.**

| Measure | Tuning set, before the changes | Tuning set, after | **Fresh set** |
|---|---|---|---|
| **Strict:** fields with one right answer, as expected | 205 of 267 | 251 of 267 | **258 of 283** |
| **Judgment calls:** two answers right, either given | 39 of 69 | 67 of 69 | **45 of 53** |
| False passes | 1 | 1 | **6** (3 labels, both copies) |
| Planted problems shown as Problem | 24 of 24 | 23 of 24 | **22 of 24** (2 as Check this) |
| Issues flagged on the labels as approved | 62 | 31 | **33** |
| Of those, false Problems (the key says the field is fine) | 41 | 5 | **9** |
| Conditions TTB noted on things the tool checks, flagged | 6 of 7 | 6 of 7 | **5 of 6** (4 for TTB's reason) |
| Checks under 5 seconds | 47 of 48 | 48 of 48 | **47 of 48** |
| AI cost | about 4 cents | about 4 cents | about 4 cents |

Details: [first run](measurements/real-labels-2026-10-20.md),
[tuning set after the changes](measurements/real-labels-2026-10-20-tuning.md),
[fresh set](measurements/real-labels-2026-10-20-fresh.md).

**The first run** found that the comparisons were too literal for real labels: "LLC" left out,
the state spelt out, a street address added, a fanciful name read as the brand, a class printed
with other words, keg labels listing several sizes. Claude mostly read the labels correctly.

**The changes** (see [APPROACH.md](APPROACH.md)): the bottler's company, city, and state are
compared rather than its exact words, and a different company name in the same city and state
needs review as a possible trade name; the application's whole brand is looked for elsewhere on
the label; a class printed with other words matches unless a word that makes a different class
is among them; a size given twice counts once and several listed sizes need review; and the
warning gets a second reading by Tesseract. A test makes sure no name from either set is in the
app's code.

**The fresh set** has fewer false Problems than before the changes (9 against 41), but more
false passes than the tuning set (6 against 1):

- An alcohol statement in a form TTB doesn't allow ("BY/VOL") passed the form check. TTB noted it.
- A misspelt word in a warning's heading: Claude read it spelt correctly, and the second reading
  didn't run, because it finds the warning by its heading.
- A front label whose net contents contradict the back label's: Claude read the back label's.

On another label, Claude read a misspelt word in the warning spelt correctly and the second
reading caught it. Some approved labels contain warning-text differences that the tool flags,
including some TTB didn't mention.

**Found by the fresh set, and not fixed.** Changing the rules now would make the fresh set a
tuning set too, so these are listed, not fixed. A third set would be needed to measure fixes.

- Bugs: "1 pint (16 fl oz)" is added up to 2 pints; a company name with a digit in it
  is taken for a street address.
- The second reading finds the warning by its heading, so a misspelt heading defeats it; and it
  can read text beside the warning into it.
- The alcohol form check accepts "BY/VOL"; an alcohol range ("11-14%") is compared as one number.
- Brands in stylized lettering that neither reader reads are still missed when Claude takes
  another name for the brand.

## Limits of this evaluation

- **The sample labels are drawn by code,** by the same project that wrote the rules. Real
  labels have curved bottles, foil, embossing, script fonts, and busy artwork. The real labels
  are a check on that, but they are the artwork submitted to TTB, not photos of bottles, and
  24 fresh labels is a small set.
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
uv run python -m tools.time_live --url https://... --sample all --runs 2  # every sample, twice
uv run python -m tools.evaluate --only old-tom-bourbon     # some labels only
uv run --env-file .env python -m tools.evaluate --cases private/cola-fresh/cases.json  # real labels, kept private
```

Each run with Claude costs about two cents; against a deployed app, about four, because each
label is read twice. A slow answer asked for again adds one more request. Results are saved to
`docs/measurements/` as JSON and Markdown, exactly as measured.
