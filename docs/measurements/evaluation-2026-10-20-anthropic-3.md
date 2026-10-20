# Evaluation, 2026-10-20T07:28:42

Mode: in process, reader `anthropic`, settings `{'model': 'claude-haiku-5-5', 'thinking': 'off', 'effort': 'low', 'max_image_edge': 1568}`.

Commit: `2ebfda9`.

## Summary

| Measure | Result |
|---|---|
| Labels | 31 (23 clean, 8 photo-like) |
| Errors | 0 |
| Clean labels with every field as expected | 22 of 23 |
| Photo-like label fields with an acceptable result | 56 of 56 |
| False passes (a planted problem shown as Matches) | 1 |
| False fails (a Problem where none was planted) | 0 |
| Clean label fields read exactly as printed | 159 of 161 |
| Time per label (median / p95 / max) | 2.6 s / 3.61 s / 3.71 s |
| Labels checked in under 5 seconds | 31 of 31 |
| Fields to look at that were outlined on the picture | 16 of 21 |
| Checks where Tesseract's second reading was ready in time | 31 of 31 |
| AI cost for this run (estimate from tokens) | $0.0244 |

Field results by kind: exact 216, false pass 1.

## False passes

- northvale-whisky-warning-not-bold: government_warning

## By label

| Label | Photo | Time | Result |
|---|---|---|---|
| old-tom-bourbon |  | 3.09 s | all fields as expected |
| stones-throw-gin |  | 2.74 s | all fields as expected |
| ridgewick-rye-wrong-abv |  | 3.09 s | all fields as expected |
| harborlume-rum-proof |  | 2.6 s | all fields as expected |
| copperfen-vodka-title-case-warning |  | 2.75 s | all fields as expected |
| heronmere-gin-warning-wording |  | 2.41 s | all fields as expected |
| northvale-whisky-warning-not-bold |  | 3.71 s | 1 false pass |
| saltreed-vodka-net-contents |  | 2.46 s | all fields as expected |
| chateau-landrevin-wine |  | 2.67 s | all fields as expected |
| tidewick-pale-ale |  | 2.29 s | all fields as expected |
| granitefall-bourbon-prompt-injection |  | 2.91 s | all fields as expected |
| seiran-japanese-whisky |  | 2.27 s | all fields as expected |
| kirchberger-german-lager |  | 2.68 s | all fields as expected |
| silverbirch-vodka-centiliters |  | 2.68 s | all fields as expected |
| driftwood-rum-no-warning |  | 2.24 s | all fields as expected |
| meadowvine-table-wine |  | 2.3 s | all fields as expected |
| irongate-bourbon-proof-only |  | 2.37 s | all fields as expected |
| lakemoor-lager-metric-only |  | 2.86 s | all fields as expected |
| fernhollow-gin-unauthorized-size |  | 3.01 s | all fields as expected |
| verdale-dessert-wine-no-alcohol |  | 2.65 s | all fields as expected |
| tallgrass-bourbon-two-sides |  | 2.68 s | all fields as expected |
| silvernook-whiskey-no-bottled-by |  | 2.56 s | all fields as expected |
| cerro-plateado-tequila |  | 3.61 s | all fields as expected |
| stones-throw-gin--tilted | tilted | 2.68 s | all fields as expected |
| ridgewick-rye-wrong-abv--angled | angled | 2.57 s | all fields as expected |
| heronmere-gin-warning-wording--blurry | blurry | 2.44 s | all fields as expected |
| copperfen-vodka-title-case-warning--dim | dim | 2.45 s | all fields as expected |
| saltreed-vodka-net-contents--glare | glare | 2.6 s | all fields as expected |
| tidewick-pale-ale--far | far | 2.48 s | all fields as expected |
| northvale-whisky-warning-not-bold--tilted | tilted | 2.53 s | all fields as expected |
| harborlume-rum-proof--glare | glare | 2.31 s | all fields as expected |

## Notes

Run after the bold question was rewritten (commit `2ebfda9`). The false pass is again the sample
whose warning heading isn't bold. Over 19 readings of that sample with this prompt, Claude said
"bold" 4 times; see "Bold type" in [APPROACH.md](../APPROACH.md).
