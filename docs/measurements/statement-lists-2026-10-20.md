# The reader with and without its statement lists, 2026-10-20

The reader as it is, against the same reader with the statement lists (the prompt's paragraph and the schema's two fields) taken out. Each label read once by each, in random order, one request at a time, with no second request. Measured in process, from a home connection, with the same requests as `tools/statement_lists.py` (run from a scratch copy before the tool was committed; the tool wrote these totals from the saved rows). Only totals are published. AI cost: about $0.13.

## Real labels, private set cola-fourth (24 labels)

| Reader | Requests | Output tokens (median) | Seconds (median / p95 / max) | Over 4 s |
|---|---|---|---|---|
| without lists | 48 | 558 | 2.75 s / 3.44 s / 3.79 s | 0 |
| with lists | 48 | 602 | 2.85 s / 3.67 s / 7.39 s | 2 |
| Difference, label by label (48 pairs) | | +41 | +0.04 s median, +0.16 s mean; slower with lists in 26 of 48 | |

## The sample labels (32 labels)

| Reader | Requests | Output tokens (median) | Seconds (median / p95 / max) | Over 4 s |
|---|---|---|---|---|
| without lists | 32 | 434 | 2.48 s / 2.83 s / 2.99 s | 0 |
| with lists | 32 | 476 | 2.46 s / 2.99 s / 3.99 s | 0 |
| Difference, label by label (32 pairs) | | +44 | +0.04 s median, +0.10 s mean; slower with lists in 17 of 32 | |

## All (160 requests)

| Reader | Requests | Output tokens (median) | Seconds (median / p95 / max) | Over 4 s |
|---|---|---|---|---|
| without lists | 80 | 455 | 2.61 s / 3.26 s / 3.79 s | 0 |
| with lists | 80 | 496 | 2.65 s / 3.64 s / 7.39 s | 2 |
| Difference, label by label (80 pairs) | | +41 | +0.04 s median, +0.14 s mean; slower with lists in 43 of 80 | |
