# Evaluation, 2026-10-19T08:47:29

Mode: in process, reader `anthropic`, settings `{'model': 'claude-haiku-5-5', 'thinking': 'off', 'effort': 'low', 'max_image_edge': 1568}`.

Commit: `487a0c4`.

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
| Time per label (median / p95 / max) | 2.38 s / 3.39 s / 4.21 s |
| Labels checked in under 5 seconds | 31 of 31 |
| AI cost for this run (estimate from tokens) | $0.0219 |

Field results by kind: exact 216, review instead of fail 1.

## By label

| Label | Photo | Time | Result |
|---|---|---|---|
| old-tom-bourbon |  | 3.38 s | all fields as expected |
| stones-throw-gin |  | 2.27 s | all fields as expected |
| ridgewick-rye-wrong-abv |  | 2.45 s | all fields as expected |
| harborlume-rum-proof |  | 2.23 s | all fields as expected |
| copperfen-vodka-title-case-warning |  | 2.59 s | all fields as expected |
| heronmere-gin-warning-wording |  | 2.38 s | all fields as expected |
| northvale-whisky-warning-not-bold |  | 2.53 s | all fields as expected |
| saltreed-vodka-net-contents |  | 2.26 s | all fields as expected |
| chateau-landrevin-wine |  | 2.55 s | all fields as expected |
| tidewick-pale-ale |  | 2.11 s | all fields as expected |
| granitefall-bourbon-prompt-injection |  | 2.45 s | all fields as expected |
| seiran-japanese-whisky |  | 2.07 s | all fields as expected |
| kirchberger-german-lager |  | 2.54 s | all fields as expected |
| silverbirch-vodka-centiliters |  | 2.55 s | all fields as expected |
| driftwood-rum-no-warning |  | 2.1 s | all fields as expected |
| meadowvine-table-wine |  | 2.55 s | all fields as expected |
| irongate-bourbon-proof-only |  | 2.14 s | all fields as expected |
| lakemoor-lager-metric-only |  | 2.67 s | all fields as expected |
| fernhollow-gin-unauthorized-size |  | 2.25 s | all fields as expected |
| verdale-dessert-wine-no-alcohol |  | 2.06 s | all fields as expected |
| tallgrass-bourbon-two-sides |  | 2.34 s | all fields as expected |
| silvernook-whiskey-no-bottled-by |  | 2.26 s | all fields as expected |
| cerro-plateado-tequila |  | 2.33 s | all fields as expected |
| stones-throw-gin--tilted | tilted | 4.21 s | all fields as expected |
| ridgewick-rye-wrong-abv--angled | angled | 2.35 s | all fields as expected |
| heronmere-gin-warning-wording--blurry | blurry | 3.39 s | 1 review instead of fail |
| copperfen-vodka-title-case-warning--dim | dim | 2.42 s | all fields as expected |
| saltreed-vodka-net-contents--glare | glare | 2.08 s | all fields as expected |
| tidewick-pale-ale--far | far | 2.25 s | all fields as expected |
| northvale-whisky-warning-not-bold--tilted | tilted | 3.31 s | all fields as expected |
| harborlume-rum-proof--glare | glare | 2.42 s | all fields as expected |
