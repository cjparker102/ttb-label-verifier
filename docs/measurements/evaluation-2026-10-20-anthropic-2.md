# Evaluation, 2026-10-20T07:23:44

Mode: in process, reader `anthropic`, settings `{'model': 'claude-haiku-5-5', 'thinking': 'off', 'effort': 'low', 'max_image_edge': 1568}`.

Commit: `0740a5a`.

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
| Time per label (median / p95 / max) | 2.59 s / 3.98 s / 6.5 s |
| Labels checked in under 5 seconds | 30 of 31 |
| Fields to look at that were outlined on the picture | 16 of 22 |
| Checks where Tesseract's second reading was ready in time | 31 of 31 |
| AI cost for this run (estimate from tokens) | $0.0251 |

Field results by kind: exact 214, extra review 1, false pass 1, review instead of fail 1.

## False passes

- northvale-whisky-warning-not-bold: government_warning

## By label

| Label | Photo | Time | Result |
|---|---|---|---|
| old-tom-bourbon |  | 6.5 s | all fields as expected |
| stones-throw-gin |  | 3.24 s | all fields as expected |
| ridgewick-rye-wrong-abv |  | 2.56 s | all fields as expected |
| harborlume-rum-proof |  | 2.59 s | all fields as expected |
| copperfen-vodka-title-case-warning |  | 2.79 s | all fields as expected |
| heronmere-gin-warning-wording |  | 2.26 s | all fields as expected |
| northvale-whisky-warning-not-bold |  | 3.98 s | 1 false pass |
| saltreed-vodka-net-contents |  | 2.55 s | all fields as expected |
| chateau-landrevin-wine |  | 2.63 s | all fields as expected |
| tidewick-pale-ale |  | 2.64 s | all fields as expected |
| granitefall-bourbon-prompt-injection |  | 2.54 s | all fields as expected |
| seiran-japanese-whisky |  | 2.46 s | all fields as expected |
| kirchberger-german-lager |  | 2.9 s | all fields as expected |
| silverbirch-vodka-centiliters |  | 2.59 s | all fields as expected |
| driftwood-rum-no-warning |  | 2.17 s | all fields as expected |
| meadowvine-table-wine |  | 2.49 s | all fields as expected |
| irongate-bourbon-proof-only |  | 2.59 s | all fields as expected |
| lakemoor-lager-metric-only |  | 2.46 s | all fields as expected |
| fernhollow-gin-unauthorized-size |  | 3.24 s | all fields as expected |
| verdale-dessert-wine-no-alcohol |  | 2.54 s | all fields as expected |
| tallgrass-bourbon-two-sides |  | 3.56 s | all fields as expected |
| silvernook-whiskey-no-bottled-by |  | 2.74 s | all fields as expected |
| cerro-plateado-tequila |  | 2.54 s | all fields as expected |
| stones-throw-gin--tilted | tilted | 2.15 s | all fields as expected |
| ridgewick-rye-wrong-abv--angled | angled | 2.97 s | all fields as expected |
| heronmere-gin-warning-wording--blurry | blurry | 2.44 s | 1 review instead of fail |
| copperfen-vodka-title-case-warning--dim | dim | 2.58 s | all fields as expected |
| saltreed-vodka-net-contents--glare | glare | 2.41 s | 1 extra review |
| tidewick-pale-ale--far | far | 2.68 s | all fields as expected |
| northvale-whisky-warning-not-bold--tilted | tilted | 2.8 s | all fields as expected |
| harborlume-rum-proof--glare | glare | 3.23 s | all fields as expected |

## Notes

Run after the AI reader was asked to list every alcohol and net contents statement (commit
`0740a5a`). The false pass is the sample whose warning heading isn't bold: Claude said it looks
bold. Reading that sample again 6 times, this prompt said "bold" 6 times, and the prompt before
it 2 times in 6, so the bold question was rewritten (next run).
