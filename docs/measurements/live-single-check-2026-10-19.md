# Single-check time on the deployed app, 2026-10-19

How long an agent waits for one label's result on the live app, from pressing Check to
seeing the page. Claude Haiku 5.5 does the reading. Every check was sent from a home
connection in the US, one at a time, with `tools/evaluate.py --url` or `tools/time_live.py`.

Two times are given for each check:

- **End to end:** measured on this computer, from sending the form to receiving the whole
  results page. It includes the upload.
- **Inside the app:** the page's "Checked in" time, from the pictures arriving to the result
  being ready. It includes shrinking the pictures, Claude's reading, the rules, and the wait
  for outlines.

## The outline wait

Tesseract looks for the words on the picture while Claude reads. When Claude finishes first,
the check waits at most 1 second more for the outlines, and logs "Outlines skipped" if it
gives up. Across all 42 checks in this note, the app's logs show no warnings at all. So
the outline wait never reached its 1-second limit, and whatever it added is already inside
the times below.

## Warm app, sample labels

The 31 sample labels, as drawn (PNG, 0.15 to 0.3 MB a picture). This was the single-check
part of the deployed evaluation
([evaluation-2026-10-19-deployed.md](evaluation-2026-10-19-deployed.md)), run on revision
`ttb-label-verifier--0000017`, image `223172b`.

| Measure | End to end | Inside the app |
|---|---|---|
| Median | 2.95 s | 2.8 s |
| p95 | 4.65 s | 4.5 s |
| Slowest | 8.79 s | 8.6 s |
| Under 5 seconds | 30 of 31 | |

Upload and page download added 0.05 to 0.34 s. The one slow check (the dim photo of the
title-case warning label) spent 8.6 s inside the app. No warning or error was logged, and
the outline was drawn, so the time went to Claude's answer. The in-process runs saw the same
occasional slow answer from the API (EVALUATION.md, "Speed varies between runs").

## Warm app, phone-sized photos

A real phone photo is about 4032 by 3024 pixels and 3 to 6 MB as a JPEG. `tools/time_live.py
--phone` blows a sample up to that width and adds camera-like grain, so the JPEG is that
large. Run on revision `ttb-label-verifier--0000018`, image `b77edd8`. The checking code is
the same as in revision 17; only the usage limits and the batch memory cap changed.

| Label | Upload | Runs | End to end (median, range) | Inside the app (median) |
|---|---|---|---|---|
| `ridgewick-rye-wrong-abv--angled`, 1 picture | 6.0 MB | 5 | 3.47 s (3.08 to 3.74 s) | 2.7 s |
| `tallgrass-bourbon-two-sides`, 2 pictures | 11.9 MB | 3 | 4.17 s (4.08 to 4.25 s) | 3.0 s |

Inside the app, the big photos took no longer than the small sample pictures (2.7 s against
2.8 s median), because every picture is shrunk to 1568 pixels before Claude sees it. The
extra time is the upload: about 0.8 s for one 6 MB photo and 1.2 s for two, on this
connection. Every run outlined its one field to look at.

## Cold app: the first check after the app has scaled to zero

The app scales to zero replicas after about 5 minutes without requests. A check was then
sent to `ridgewick-rye-wrong-abv`, followed by two more.

| Check | End to end | Inside the app |
|---|---|---|
| First, cold | **26.62 s** | 3.4 s |
| Second | 2.94 s | 2.8 s |
| Third | 3.94 s | 3.8 s |

Where the 23 seconds before the check went, from Azure's system log:

| Time (UTC) | Step |
|---|---|
| 23:03:13 | Request sent |
| 23:03:15 | Replica created |
| 23:03:17 to 23:03:23 | Image pulled (189 MB, 5.5 s) |
| 23:03:23 to 23:03:31 | Container created (8 s) |
| 23:03:31 to 23:03:33 | App started (2 s) |
| 23:03:33 to about 23:03:38 | Azure's startup probe and routing (about 5 s) |
| about 23:03:38 to 23:03:41 | The check itself (3.4 s) |

The same wait falls on whatever request comes first after a quiet spell, usually the home
page. After that, pages load in about 0.05 s. Keeping one replica running would remove it.
That is a cost decision, still open.
