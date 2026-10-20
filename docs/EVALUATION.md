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

There are 32 labels in `samples/`, drawn by `tools/make_samples.py` with made-up brands:

- **24 clean labels.** Four have nothing wrong; one of these, added on Oct 20, copies three
  things a real bottle photo tripped over (a fanciful name larger than the brand with the
  class small on the back, the warning's heading on a line of its own, and "ALC." before the
  alcohol figure). The others each plant one or more known problems, covering every rule:
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

`samples/expected.json` holds the expected result for every field of every label (224 field
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

The latest runs, on Oct 20, 2026, after the changes for a real bottle photo (commit
`8b1d574`, see below), with the new sample that copies it: in process, with the app's default
settings (1568-pixel pictures, thinking off, low effort) and outlines on, as in a single
check. Three runs were made; the table is the first. Full results:
[evaluation-2026-10-20-anthropic-4.md](measurements/evaluation-2026-10-20-anthropic-4.md),
[-5](measurements/evaluation-2026-10-20-anthropic-5.md),
[-6](measurements/evaluation-2026-10-20-anthropic-6.md).

| Measure | Result |
|---|---|
| False passes | **0** of 224 field results (1 in the second run, 0 in the third) |
| False fails | **0** in all three runs |
| Field results as expected | 224 of 224, counting Check this on a photo-like label and a note on a match as acceptable |
| Clean label fields read exactly as printed | 165 of 168 |
| Time per label (median / p95 / max) | 2.66 s / 3.48 s / 3.56 s |
| Labels checked in under 5 seconds | 32 of 32, in all three runs |
| Fields to look at that were outlined on the picture | 17 of 23 |
| Checks where Tesseract's second reading was ready in time | 32 of 32 |
| AI cost for the 32 labels (estimate from tokens) | $0.026, about 0.08 cents a label |

The second run's false pass is the known one: the warning heading that isn't bold, read as
bold. The new sample was read whole in all three runs: its class on the back, "ALC. 5% BY VOL",
and the warning with its heading. Claude read its brand as "VESPERLY MOONLIT BRAMBLE", which
matches with a note. The third run is marked "-dirty" only because this page was being edited
while it ran; the app's code was `8b1d574`.

Earlier, on Oct 20 before these changes, a run of the 31 samples then had all but one field
as expected ([evaluation-2026-10-20-anthropic.md](measurements/evaluation-2026-10-20-anthropic.md)),
and the Oct 19 run, before the changes for real labels, had all 217 as expected
([evaluation-2026-10-19-anthropic.md](measurements/evaluation-2026-10-19-anthropic.md)).

The three clean fields not read exactly didn't change any result:

- On the label whose warning heading is not bold, Claude said it couldn't tell whether the
  heading was bold, rather than "no". The rule treats anything short of a clear yes as
  Check this, which is the expected result.
- On the French wine, Claude copied both "Mis en bouteille au château" and the "Imported by"
  statement, as its instructions now say. The answer key lists only the importer statement.
- On the new sample, Claude read the brand with the fanciful name under it, "VESPERLY MOONLIT
  BRAMBLE". The application's brand is in it, so it matches with a note.

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

### Did the statement lists slow the reader? (Oct 20)

The fourth set of real labels had 4 of 48 checks over 5 seconds, against none on the third.
It was also the first set read since Claude was asked to list every alcohol and net contents
statement. In the fourth set's run, 8 of 48 checks had no answer after 4 seconds and were
asked again; its slow checks' token counts are doubled because both requests are paid for,
which made them look like long readings. Per request, output went from a median of 568
tokens (third set) to 594.

So the reader was measured with and without the lists, on the same labels: the fourth set's
24 twice and the 32 samples once, each label read by both, in random order, one request at a
time, with no second request
([statement-lists-2026-10-20.md](measurements/statement-lists-2026-10-20.md)).

| | Without lists | With lists |
|---|---|---|
| Output tokens, median | 455 | 496 (+41 a label) |
| Seconds, median / p95 | 2.61 / 3.26 | 2.65 / 3.64 |
| Paired difference, label by label | | +0.04 s median, +0.14 s mean; slower in 43 of 80 pairs |
| Requests over 4 seconds | 0 of 80 | 2 of 80 (7.4 s and 4.2 s) |

The lists cost about 40 output tokens and a few hundredths of a second, not the slow checks.
The two slow requests wrote about 600 tokens, like their pairs, and the same labels with the
same reader took 2.6 s in the other round; and the fourth set's 24 labels, read again with
the lists, were slow 2 times in 48 instead of 8. The slow checks were slow answers from the
AI provider at the time of the run. The lists were kept as they are.

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
would take about 9 minutes instead of about 2.

So for review week the app was given 2 CPUs and 4 GiB (revision 22, the same image). Two
batches of the 31 labels then took 32.7 s and 29.5 s: about 1.0 s a label, so about 5 minutes
for 300. The "try again in N minutes" estimate now counts 1.2 s a label.

Revision 23 (image `e72cc4c`: that estimate, and the two fixes for false passes found by the
fresh set, below), on 2 CPUs: every sample as expected, no false passes or false Problems, 31 of
31 single checks under 5 seconds (median 2.88 s, slowest 4.44 s), the second reading ready on all
31, and the batch in 28.6 s. Details:
[evaluation-2026-10-20-deployed-3.md](measurements/evaluation-2026-10-20-deployed-3.md).

### Oct 20, night: revision 25, and a batch of 300

After the changes from ChatGPT's review (revision 25, image `77dd73a`, 2 CPUs), the evaluation
was run on the live app again
([evaluation-2026-10-20-deployed-4.md](measurements/evaluation-2026-10-20-deployed-4.md)), and
then a batch of 300 rows, the 31 samples repeated, twice with `tools/batch_live.py`
([first](measurements/batch-300-2026-10-20.md),
[second](measurements/batch-300-2026-10-20-0911.md)).

| Measure | Result |
|---|---|
| Single checks, end to end (median / p95 / max) | 2.89 s / 3.85 s / 4.83 s, 31 of 31 under 5 s |
| Batch of 31 | 30.3 s, every label read by Claude |
| Field results, batch of 31 | as expected, but for 1 false pass (a warning heading that isn't bold, read as bold) |
| **Batch of 300** | **4.5 and 4.1 minutes**, 0.90 and 0.82 s a label; all 300 read by Claude both times |
| Rows of 300 with every field as expected | 294 and 297 |
| What the rest were | First run: 5 false passes and 1 false Problem, not recorded by sample. Second: the not-bold heading read as bold on 2 of its 10 rows, and a French importer statement read differently once |

The 8-second reading deadline never sent a batch label to basic text reading: Claude answered
every one in time, with 8 read at once.

### Oct 20, afternoon: revision 26, with the fixes for a real bottle photo

Revision 26 (image `71177c1`, 2 CPUs) adds the changes for a real bottle photo and the 32nd
sample ([evaluation-2026-10-20-deployed-5.md](measurements/evaluation-2026-10-20-deployed-5.md)).

| Measure | Result |
|---|---|
| Single checks, end to end (median / p95 / max) | 2.85 s / 3.95 s / 5.84 s, 31 of 32 under 5 s |
| Batch of 32 | 31.9 s, every label read by Claude |
| Field results, batch of 32 | no false passes and no false Problems; the new sample as expected, its brand read with the fanciful name (a note) |

The check over 5 seconds spent 5.7 s inside the app, so the wait was the AI provider's answer.

Revision 27 (image `1f7ef3c`) adds the decimal-comma check and the new sample on the home page
([evaluation-2026-10-20-deployed-6.md](measurements/evaluation-2026-10-20-deployed-6.md)):
single checks 2.88 s / 4.31 s / 4.70 s (median / p95 / max), 32 of 32 under 5 seconds; a batch
of 32 in 30.1 s; no false passes or false Problems.

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

Approved labels from TTB's Public COLA Registry, in four sets of 24 (8 spirits, 8 wine, and 8
malt beverages each, all received in 2026). Each label was checked twice, once as approved and
once with one problem planted in its application data: 48 checks a set, in process, with the
app's default settings. The pictures, application data, answer keys, and per-label results are
kept private and never committed. Only totals, the TTB IDs, and the results for the planted
problems, which are made up, are published.

- **How they were chosen:** by a rule fixed before looking at any label. For each slot (a
  class/type code, domestic or imported), the first approved label approval with a picture, in
  the registry's own order, one per company. The registry was asked slowly, 3 seconds between
  requests. Each set skipped the earlier sets' labels and companies.
- **The application data:** brand name from the registry, word for word. Bottler or importer:
  the company the registry lists, with its city and state. Country of origin from the registry.
  Class, alcohol content, and net contents were copied from the label, because the registry has
  no such fields.
- **The answer keys** were checked by Christopher against every picture before each set's first
  run, including every flaw seen on the approved labels. Some answers are judgment calls, where
  two results are right (Matches or Check this for a warning that may be bold, for example).
  Accuracy is given separately for these, never combined.

### Five runs on four sets

The first run showed far too many false Problems, so the rules were changed, using that set's
labels: the **tuning set**. A **fresh set** was then chosen and checked once; it found two
gaps behind false passes, which were fixed, so it became tuning too. A **third set** was then
chosen and checked once; the gaps it found were fixed on the night of Oct 20, so it became
tuning as well. A **fourth set** was then chosen and checked once, at commit `6530f56`, with
nothing in the app changed since its labels were seen. **The fourth set is the honest
number.**

| Measure | Tuning set, before the changes | Tuning set, after | Fresh set | Third set | **Fourth set** |
|---|---|---|---|---|---|
| **Strict:** fields with one right answer, as expected | 205 of 267 | 251 of 267 | 258 of 283 | 256 of 280 | **252 of 274** |
| **Judgment calls:** two answers right, either given | 39 of 69 | 67 of 69 | 45 of 53 | 50 of 56 | **50 of 62** |
| False passes | 1 | 1 | 6 | 0 | **2** (one label, in both its checks) |
| Planted problems shown as Problem | 24 of 24 | 23 of 24 | 22 of 24 | 23 of 24 (1 as Check this) | **24 of 24** |
| Of those, **detected**: raised by the field's comparison with the application | | | | 22 of 24 | **24 of 24** |
| Flagged for **another reason** (print too hard to read, a statement missing) | | | | 2 (1 Problem, 1 Check this) | **0** |
| Issues flagged on the labels as approved | 62 | 31 | 33 | 31 | **34** |
| Of those, false Problems (the key says the field is fine) | 41 | 5 | 9 | 9 | **11** |
| Conditions TTB noted on things the tool checks, flagged | 6 of 7 | 6 of 7 | 5 of 6 | 2 of 2 | **1 of 2** |
| Checks under 5 seconds | 47 of 48 | 48 of 48 | 47 of 48 | 48 of 48 | **44 of 48** (slowest 7.2 s) |
| AI cost | about 4 cents | about 4 cents | about 4 cents | about 4 cents | about 5 cents |

Details: [first run](measurements/real-labels-2026-10-20.md),
[tuning set after the changes](measurements/real-labels-2026-10-20-tuning.md),
[fresh set](measurements/real-labels-2026-10-20-fresh.md),
[third set](measurements/real-labels-2026-10-20-third.md),
[fourth set](measurements/real-labels-2026-10-20-fourth.md).

**The first run** found that the comparisons were too literal for real labels: "LLC" left out,
the state spelt out, a street address added, a fanciful name read as the brand, a class printed
with other words, keg labels listing several sizes. Claude mostly read the labels correctly.

**The changes** (see [APPROACH.md](APPROACH.md)): the bottler's company, city, and state are
compared rather than its exact words, and a different company name in the same city and state
needs review as a possible trade name; the application's whole brand is looked for elsewhere on
the label; a class printed with other words matches unless a word that makes a different class
is among them; a size given twice counts once and several listed sizes need review; and the
warning gets a second reading by Tesseract. A test makes sure no name from any set is in code
written after that set was fetched.

**The fresh set** had 6 false passes, on 3 labels: an alcohol statement in a form TTB doesn't
allow ("BY/VOL"), a misspelt warning heading that Claude read spelt correctly, and a front
label whose net contents contradict the back label's. Two of these gaps were then fixed,
generally: the alcohol form check for spirits now follows the three formats of 27 CFR
5.65(b)(2) exactly, and the second reading finds the warning by its text when it can't find the
heading. (On that label the second reading still can't help: one of Tesseract's passes can't
read its stylized lettering, and both must agree.)

**The third set** had no false passes, and all 22 planted problems on fields that were fine on
the unchanged label were shown as Problem. Counting how each planted problem was caught: 22 were
**detected**, raised by the field's comparison with the application; 2 were flagged for
**another reason**: a label with no country of origin statement at all (Problem), and a bottler
statement Claude found hard to read (Check this). The planted problems are published label by
label in [the third set's note](measurements/real-labels-2026-10-20-third.md); the real labels'
own results are not. The changed alcohol form check flagged one statement
without "by" or a slash. Both conditions TTB noted were flagged, for TTB's reasons. Some approved
labels contain warning-text differences that TTB didn't mention: the tool flagged a space before
the heading's colon and a missing final period as Check this, but missed square brackets around
the statement numbers, which Claude read as parentheses. It still shows 9 false Problems:

- "1 pint (16 fl oz)" is added up to 2 pints (2 labels): a bug the fresh set found, fixed after
  this run (below).
- A country of origin stated only inside the bottler statement ("bottled in Scotland") isn't
  found (2 labels).
- A brand isn't found when Claude takes another name for it and the application's brand is under
  6 letters (so not looked for), written differently on the label, or split across lines (3).
- Claude read a type word for the class ("Añejo"), and read the line after the warning into it.

**Fixed after the third set's run: one bug.** The same amount written in two units, as in "1
PINT (16 FL OZ)", now counts once instead of adding up; amounts in falling units still add up
when each is less than one of the unit before it ("1 PINT 9 FL OZ"). **The third-set numbers
above were measured before this fix.** Replaying that run's saved readings through the fixed
rule, strict goes from 256 to 260 of 280: the 4 net contents false Problems on 2 labels become
Matches, and nothing else changes. That set has now been seen, so this is not an honest
measure of the fix. The 31 samples are unchanged.

**Changed after the third set (the night of Oct 20).** General rules, not fixes for single
labels; the fourth set is their honest measure.

- A company name with a digit in it stays the company, not a street address.
- A country named only in the bottler statement ("bottled in Scotland") gives Check this.
- An alcohol range ("11-14%") always gives Check this, never one number.
- A short brand found elsewhere, or a brand written differently (run together, another company
  form), gives Check this, not Problem.
- Claude lists every alcohol and net contents statement it sees; if they disagree, or a metric
  amount disagrees with its US one, Check this.

Not changed: the second reading compares words only, so it can't catch a missing comma or
brackets read as parentheses; and Claude sometimes reads a type word ("Blanco", "Añejo") as the
class, or text next to a field into it.

**The fourth set** had all 24 planted problems detected by the comparison and shown as
Problem. Two warning errors on approved labels that TTB didn't mention, a misspelt word and a
heading in title case, were both shown as Problem. Its 2 false passes are one label, checked
twice: an alcohol statement with a decimal comma ("5,8 %") was read as 5.8% and matched. TTB's
approval asked for that statement to be changed to an allowed form, so it is also the one TTB
condition missed. Its 11 false Problems, on 8 labels:

- The registry's brand isn't the name the label shows as its brand (5 labels). It adds the type
  or a company word to it (2); it is the beer's style, which Claude read as the class, and a
  class is never taken for the brand (2); or it is a product name neither reader found as a
  whole phrase (1).
- Claude misread or missed a field (4 labels, 5 fields): a wine's vineyard name taken for its
  class, and its alcohol statement on the back label missed; a country of origin missed; an
  imported label's bottler statement read in place of its importer statement; a warning read
  without its heading.
- A class shorter on the label than in the application ("Stout" for "Stout Ale").

4 of its 48 checks took over 5 seconds (the slowest 7.2 s), against none on the third set; the
median, 3.0 s, was close to the third set's 2.8 s. The cause was slow answers from the AI
provider during the run, not the statement lists (see "Did the statement lists slow the
reader?" above). No rule was changed because of this set.

**Changed afterwards, for a real bottle photo (Oct 20, afternoon).** A photo of a real bottle
found three things: a warning heading on a line of its own that Claude left out, a fanciful
name Claude took for the class (printed small on the back), and "ALC." dropped from the
alcohol statement. The changes (see [APPROACH.md](APPROACH.md)): a heading seen elsewhere
counts as present, and a missing heading alone is Check this; the application's class found
elsewhere on the label is used in place of what Claude read; Claude is told to copy the whole
alcohol statement; and an alcohol content the application gives but the label doesn't show
needs review even where the label may leave it out. Replaying this set's saved readings
through the changed rules (no AI request, Tesseract given all the time it needs, commit
`8b1d574`), 3 of the 11 false Problems become right: the wine's class is found on its back
label, its missed alcohol range becomes Check this, and the warning read without its heading
becomes Check this. Strict goes from 252 to 254 of 274, judgment calls from 50 to 52 of 62;
nothing else changes, and the decimal-comma false pass remains. Two of those false Problems
had the same causes as the photo, so this replay is not an honest measure of the changes.

**Then, the decimal comma (Christopher's decision, Oct 20).** An alcohol figure written with a
decimal comma now needs review. Among the saved readings of all four sets, only this set's
"5,8 %" statement has one, so its 2 false passes become Check this, as the key accepts; among
the samples, the French wine's "13,5% vol" already needed review for its form. With both
changes, the replayed fourth set has no false passes and 8 false Problems. Again, these labels
had been seen.

## The warning's second reading on real labels

Tesseract's second reading of the warning was replayed on all 72 real labels from the three
private sets, with each label's saved reading by Claude, and no AI request
([second-reading-2026-10-20.md](measurements/second-reading-2026-10-20.md)):

| What the second reading made of the warning | Labels |
|---|---|
| Missing: neither of Tesseract's passes read the warning | 29 |
| Missing: only one pass read it | 12 |
| Inconclusive: both read it, only one disagreed with Claude | 6 |
| Both read it and agreed with Claude | 20 |
| Both read it and disagreed: Check this | 5 (2 real misprints, 3 Tesseract noise) |

So it is missing on 57% of real labels, and gives a clear answer on about a third. It still
caught 2 misspellings Claude read as spelt correctly. The rule is unchanged.

## A code-side bold check, tried and not kept

Claude sometimes calls a heading that isn't bold "bold" (about one reading in five on the
sample made for it). As a second opinion, code measured the stroke thickness of "GOVERNMENT
WARNING" against the warning's words after it, where Tesseract found both, and would have
added Check this when the heading wasn't clearly heavier. It could never make a result a pass.
It was measured, with no AI request, on the samples and on all 96 real labels, using each
label's saved reading by Claude
([heading-weight-2026-10-20.md](measurements/heading-weight-2026-10-20.md)).

At the setting that catches the sample's false pass (heavier by less than 1.1 times, on print
at least 14 pixels tall):

| | Result |
|---|---|
| Samples: the heading that isn't bold, where Claude said bold | caught |
| Samples: 28 bold headings | no false alarms |
| Real labels: 6 headings the answer keys say aren't bold | nothing to catch: Claude said "can't tell" on all 6, so they were Check this already |
| Real labels: 71 bold headings Claude called bold | 6 false alarms, 2 of them making a right result wrong |

On the real labels it only added false alarms. Where it fails, the heading is set in a
different typeface from the rest (a condensed bold beside a heavy serif), or the print is so
small that strokes are 1 or 2 pixels wide. Measuring upright strokes alone did worse. So the
app still relies on Claude for bold, and sends every "not bold" or "can't tell" to review.

## Limits of this evaluation

- **The sample labels are drawn by code,** by the same project that wrote the rules. Real
  labels have curved bottles, foil, embossing, script fonts, and busy artwork. The real labels
  are a check on that, but they are the artwork submitted to TTB, not photos of bottles, and
  the honest measure rests on one set of 24 labels.
- **The photo-like labels are simulated** (rotated, skewed, blurred, darkened, with a glare
  spot), not taken with a camera.
- **The set is small.** No false passes in 217 field results is encouraging, but it does not
  prove the rate is zero.
- **Each label was read once per run.** Claude's times vary from run to run.
- **The live runs were from one home connection,** one check at a time. An agency network,
  or many agents at once, would give different times.

## The sample labels and tools

`tools/make_samples.py` draws the sample labels in `samples/labels/`, with made-up brands,
and writes `samples/applications.csv` and `samples/expected.json`. There are 23 labels, each
with known planted errors and the expected result for every field, plus 8 photo-like
versions (tilted, blurry, dim, glare, and so on). One label carries a prompt-injection
attempt. Regenerate with `uv run python -m tools.make_samples`. Sample labels are for
evaluation; a production version would remove them.

`tools/evaluate.py` checks every sample and records accuracy, speed, and cost in
`docs/measurements/`, in process or against the deployed app. `tools/time_live.py` times
single checks on the deployed app, with phone-sized photos if asked.
`tools/blocked_provider.py` times a check when the AI provider can't be reached,
`tools/second_reading.py` measures the warning's second reading on the private real labels,
and `tools/heading_weight.py` measures the code-side bold check that wasn't kept.

## Run it again

```sh
uv run --env-file .env python -m tools.evaluate            # Claude, in this process
uv run python -m tools.evaluate --reader ocr               # offline reader only, no cost
uv run python -m tools.evaluate --url https://... --deployed-as "revision ..., image ..."
uv run python -m tools.time_live --url https://... --phone  # phone-sized photos, timed
uv run python -m tools.time_live --url https://... --sample all --runs 2  # every sample, twice
uv run python -m tools.evaluate --only old-tom-bourbon     # some labels only
uv run --env-file .env python -m tools.evaluate --cases private/cola-fourth/cases.json  # real labels, kept private
```

Each run with Claude costs about two cents; against a deployed app, about four, because each
label is read twice. A slow answer asked for again adds one more request. Results are saved to
`docs/measurements/` as JSON and Markdown, exactly as measured.
