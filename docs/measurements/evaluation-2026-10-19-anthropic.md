# Evaluation, 2026-10-19T08:00:58

Mode: in process, reader `anthropic`, settings `{'model': 'claude-haiku-5-5', 'thinking': 'off', 'effort': 'low', 'max_image_edge': 1568}`.

Commit: `7283a69`.

## Summary

| Measure | Result |
|---|---|
| Labels | 19 (11 clean, 8 photo-like) |
| Errors | 0 |
| Clean labels with every field as expected | 11 of 11 |
| Photo-like label fields with an acceptable result | 56 of 56 |
| False passes (a planted problem shown as Matches) | 0 |
| False fails (a Problem where none was planted) | 0 |
| Clean label fields read exactly as printed | 75 of 77 |
| Time per label (median / p95 / max) | 2.46 s / 6.2 s / 6.2 s |
| Labels checked in under 5 seconds | 17 of 19 |
| AI cost for this run (estimate from tokens) | $0.0134 |

Field results by kind: exact 131, extra review 1, review instead of fail 1.

## By label

| Label | Photo | Time | Result |
|---|---|---|---|
| old-tom-bourbon |  | 3.33 s | all fields as expected |
| stones-throw-gin |  | 2.03 s | all fields as expected |
| ridgewick-rye-wrong-abv |  | 2.39 s | all fields as expected |
| harborlume-rum-proof |  | 2.72 s | all fields as expected |
| copperfen-vodka-title-case-warning |  | 5.37 s | all fields as expected |
| heronmere-gin-warning-wording |  | 6.2 s | all fields as expected |
| northvale-whisky-warning-not-bold |  | 2.46 s | all fields as expected |
| saltreed-vodka-net-contents |  | 3.77 s | all fields as expected |
| chateau-landrevin-wine |  | 3.08 s | all fields as expected |
| tidewick-pale-ale |  | 3.72 s | all fields as expected |
| granitefall-bourbon-prompt-injection |  | 2.42 s | all fields as expected |
| stones-throw-gin--tilted | tilted | 2.46 s | all fields as expected |
| ridgewick-rye-wrong-abv--angled | angled | 2.36 s | all fields as expected |
| heronmere-gin-warning-wording--blurry | blurry | 2.56 s | 1 review instead of fail |
| copperfen-vodka-title-case-warning--dim | dim | 2.33 s | all fields as expected |
| saltreed-vodka-net-contents--glare | glare | 3.83 s | 1 extra review |
| tidewick-pale-ale--far | far | 2.25 s | all fields as expected |
| northvale-whisky-warning-not-bold--tilted | tilted | 2.03 s | all fields as expected |
| harborlume-rum-proof--glare | glare | 2.46 s | all fields as expected |
