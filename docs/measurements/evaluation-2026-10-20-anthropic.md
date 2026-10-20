# Evaluation, 2026-10-20T04:12:17

Mode: in process, reader `anthropic`, settings `{'model': 'claude-haiku-5-5', 'thinking': 'off', 'effort': 'low', 'max_image_edge': 1568}`.

Commit: `4b72296`.

## Summary

| Measure | Result |
|---|---|
| Labels | 31 (23 clean, 8 photo-like) |
| Errors | 0 |
| Clean labels with every field as expected | 23 of 23 |
| Photo-like label fields with an acceptable result | 56 of 56 |
| False passes (a planted problem shown as Matches) | 0 |
| False fails (a Problem where none was planted) | 0 |
| Clean label fields read exactly as printed | 159 of 161 |
| Time per label (median / p95 / max) | 2.49 s / 3.25 s / 3.97 s |
| Labels checked in under 5 seconds | 31 of 31 |
| Fields to look at that were outlined on the picture | 17 of 23 |
| Checks where Tesseract's second reading was ready in time | 31 of 31 |
| AI cost for this run (estimate from tokens) | $0.0224 |

Field results by kind: exact 216, extra review 1.

## By label

| Label | Photo | Time | Result |
|---|---|---|---|
| old-tom-bourbon |  | 3.01 s | all fields as expected |
| stones-throw-gin |  | 2.64 s | all fields as expected |
| ridgewick-rye-wrong-abv |  | 2.94 s | all fields as expected |
| harborlume-rum-proof |  | 2.31 s | all fields as expected |
| copperfen-vodka-title-case-warning |  | 2.96 s | all fields as expected |
| heronmere-gin-warning-wording |  | 2.11 s | all fields as expected |
| northvale-whisky-warning-not-bold |  | 2.33 s | all fields as expected |
| saltreed-vodka-net-contents |  | 2.23 s | all fields as expected |
| chateau-landrevin-wine |  | 3.97 s | all fields as expected |
| tidewick-pale-ale |  | 2.63 s | all fields as expected |
| granitefall-bourbon-prompt-injection |  | 3.25 s | all fields as expected |
| seiran-japanese-whisky |  | 2.74 s | all fields as expected |
| kirchberger-german-lager |  | 2.62 s | all fields as expected |
| silverbirch-vodka-centiliters |  | 2.44 s | all fields as expected |
| driftwood-rum-no-warning |  | 2.74 s | all fields as expected |
| meadowvine-table-wine |  | 1.94 s | all fields as expected |
| irongate-bourbon-proof-only |  | 2.37 s | all fields as expected |
| lakemoor-lager-metric-only |  | 2.1 s | all fields as expected |
| fernhollow-gin-unauthorized-size |  | 2.64 s | all fields as expected |
| verdale-dessert-wine-no-alcohol |  | 2.43 s | all fields as expected |
| tallgrass-bourbon-two-sides |  | 2.34 s | all fields as expected |
| silvernook-whiskey-no-bottled-by |  | 2.34 s | all fields as expected |
| cerro-plateado-tequila |  | 2.36 s | all fields as expected |
| stones-throw-gin--tilted | tilted | 2.7 s | all fields as expected |
| ridgewick-rye-wrong-abv--angled | angled | 2.9 s | all fields as expected |
| heronmere-gin-warning-wording--blurry | blurry | 2.84 s | all fields as expected |
| copperfen-vodka-title-case-warning--dim | dim | 2.26 s | all fields as expected |
| saltreed-vodka-net-contents--glare | glare | 2.43 s | all fields as expected |
| tidewick-pale-ale--far | far | 2.24 s | 1 extra review |
| northvale-whisky-warning-not-bold--tilted | tilted | 2.76 s | all fields as expected |
| harborlume-rum-proof--glare | glare | 2.49 s | all fields as expected |
