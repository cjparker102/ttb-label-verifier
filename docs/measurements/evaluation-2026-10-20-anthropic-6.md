# Evaluation, 2026-10-20T14:17:44

Mode: in process, reader `anthropic`, settings `{'model': 'claude-haiku-5-5', 'thinking': 'off', 'effort': 'low', 'max_image_edge': 1568}`.

Commit: `8b1d574-dirty`.

## Summary

| Measure | Result |
|---|---|
| Labels | 32 (24 clean, 8 photo-like) |
| Errors | 0 |
| Clean labels with every field as expected | 23 of 24 |
| Photo-like label fields with an acceptable result | 56 of 56 |
| False passes (a planted problem shown as Matches) | 0 |
| False fails (a Problem where none was planted) | 0 |
| Clean label fields read exactly as printed | 165 of 168 |
| Time per label (median / p95 / max) | 2.56 s / 2.91 s / 2.97 s |
| Labels checked in under 5 seconds | 32 of 32 |
| Fields to look at that were outlined on the picture | 17 of 23 |
| Checks where Tesseract's second reading was ready in time | 32 of 32 |
| AI cost for this run (estimate from tokens) | $0.0256 |

Field results by kind: exact 221, extra review 1, note difference 1, review instead of fail 1.

## By label

| Label | Photo | Time | Result |
|---|---|---|---|
| old-tom-bourbon |  | 2.77 s | all fields as expected |
| stones-throw-gin |  | 2.72 s | all fields as expected |
| ridgewick-rye-wrong-abv |  | 2.58 s | all fields as expected |
| harborlume-rum-proof |  | 2.37 s | all fields as expected |
| copperfen-vodka-title-case-warning |  | 2.81 s | all fields as expected |
| heronmere-gin-warning-wording |  | 2.48 s | all fields as expected |
| northvale-whisky-warning-not-bold |  | 2.54 s | all fields as expected |
| saltreed-vodka-net-contents |  | 2.38 s | all fields as expected |
| chateau-landrevin-wine |  | 2.38 s | all fields as expected |
| tidewick-pale-ale |  | 2.46 s | all fields as expected |
| granitefall-bourbon-prompt-injection |  | 2.39 s | all fields as expected |
| seiran-japanese-whisky |  | 2.49 s | all fields as expected |
| kirchberger-german-lager |  | 2.48 s | all fields as expected |
| silverbirch-vodka-centiliters |  | 2.64 s | all fields as expected |
| driftwood-rum-no-warning |  | 2.23 s | all fields as expected |
| meadowvine-table-wine |  | 2.78 s | all fields as expected |
| irongate-bourbon-proof-only |  | 2.51 s | all fields as expected |
| lakemoor-lager-metric-only |  | 2.74 s | all fields as expected |
| fernhollow-gin-unauthorized-size |  | 2.4 s | all fields as expected |
| verdale-dessert-wine-no-alcohol |  | 2.88 s | all fields as expected |
| tallgrass-bourbon-two-sides |  | 2.64 s | all fields as expected |
| silvernook-whiskey-no-bottled-by |  | 2.78 s | all fields as expected |
| cerro-plateado-tequila |  | 2.6 s | all fields as expected |
| vesperly-wine-specialty |  | 2.65 s | 1 note difference |
| stones-throw-gin--tilted | tilted | 2.41 s | all fields as expected |
| ridgewick-rye-wrong-abv--angled | angled | 2.49 s | all fields as expected |
| heronmere-gin-warning-wording--blurry | blurry | 2.43 s | 1 review instead of fail |
| copperfen-vodka-title-case-warning--dim | dim | 2.45 s | all fields as expected |
| saltreed-vodka-net-contents--glare | glare | 2.79 s | all fields as expected |
| tidewick-pale-ale--far | far | 2.91 s | 1 extra review |
| northvale-whisky-warning-not-bold--tilted | tilted | 2.97 s | all fields as expected |
| harborlume-rum-proof--glare | glare | 2.58 s | all fields as expected |
