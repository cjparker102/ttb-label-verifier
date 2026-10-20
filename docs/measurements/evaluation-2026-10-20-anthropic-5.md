# Evaluation, 2026-10-20T14:16:20

Mode: in process, reader `anthropic`, settings `{'model': 'claude-haiku-5-5', 'thinking': 'off', 'effort': 'low', 'max_image_edge': 1568}`.

Commit: `8b1d574`.

## Summary

| Measure | Result |
|---|---|
| Labels | 32 (24 clean, 8 photo-like) |
| Errors | 0 |
| Clean labels with every field as expected | 22 of 24 |
| Photo-like label fields with an acceptable result | 56 of 56 |
| False passes (a planted problem shown as Matches) | 1 |
| False fails (a Problem where none was planted) | 0 |
| Clean label fields read exactly as printed | 165 of 168 |
| Time per label (median / p95 / max) | 2.58 s / 2.95 s / 3.03 s |
| Labels checked in under 5 seconds | 32 of 32 |
| Fields to look at that were outlined on the picture | 16 of 22 |
| Checks where Tesseract's second reading was ready in time | 32 of 32 |
| AI cost for this run (estimate from tokens) | $0.0256 |

Field results by kind: exact 220, extra review 1, false pass 1, note difference 1, review instead of fail 1.

## False passes

- northvale-whisky-warning-not-bold: government_warning

## By label

| Label | Photo | Time | Result |
|---|---|---|---|
| old-tom-bourbon |  | 2.82 s | all fields as expected |
| stones-throw-gin |  | 2.71 s | all fields as expected |
| ridgewick-rye-wrong-abv |  | 2.57 s | all fields as expected |
| harborlume-rum-proof |  | 2.56 s | all fields as expected |
| copperfen-vodka-title-case-warning |  | 2.5 s | all fields as expected |
| heronmere-gin-warning-wording |  | 3.03 s | all fields as expected |
| northvale-whisky-warning-not-bold |  | 2.44 s | 1 false pass |
| saltreed-vodka-net-contents |  | 2.63 s | all fields as expected |
| chateau-landrevin-wine |  | 2.65 s | all fields as expected |
| tidewick-pale-ale |  | 2.31 s | all fields as expected |
| granitefall-bourbon-prompt-injection |  | 2.55 s | all fields as expected |
| seiran-japanese-whisky |  | 2.63 s | all fields as expected |
| kirchberger-german-lager |  | 2.53 s | all fields as expected |
| silverbirch-vodka-centiliters |  | 2.53 s | all fields as expected |
| driftwood-rum-no-warning |  | 2.2 s | all fields as expected |
| meadowvine-table-wine |  | 2.88 s | all fields as expected |
| irongate-bourbon-proof-only |  | 2.55 s | all fields as expected |
| lakemoor-lager-metric-only |  | 2.79 s | all fields as expected |
| fernhollow-gin-unauthorized-size |  | 2.45 s | all fields as expected |
| verdale-dessert-wine-no-alcohol |  | 2.59 s | all fields as expected |
| tallgrass-bourbon-two-sides |  | 2.72 s | all fields as expected |
| silvernook-whiskey-no-bottled-by |  | 2.54 s | all fields as expected |
| cerro-plateado-tequila |  | 2.64 s | all fields as expected |
| vesperly-wine-specialty |  | 2.74 s | 1 note difference |
| stones-throw-gin--tilted | tilted | 2.5 s | all fields as expected |
| ridgewick-rye-wrong-abv--angled | angled | 2.43 s | all fields as expected |
| heronmere-gin-warning-wording--blurry | blurry | 2.53 s | 1 review instead of fail |
| copperfen-vodka-title-case-warning--dim | dim | 2.87 s | all fields as expected |
| saltreed-vodka-net-contents--glare | glare | 2.83 s | all fields as expected |
| tidewick-pale-ale--far | far | 2.95 s | 1 extra review |
| northvale-whisky-warning-not-bold--tilted | tilted | 2.85 s | all fields as expected |
| harborlume-rum-proof--glare | glare | 2.5 s | all fields as expected |
