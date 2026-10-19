# Evaluation, 2026-10-19T09:19:12

Mode: in process, reader `anthropic`, settings `{'model': 'claude-haiku-5-5', 'thinking': 'off', 'effort': 'low', 'max_image_edge': 1568}`.

Commit: `1e08341`.

## Summary

| Measure | Result |
|---|---|
| Labels | 31 (23 clean, 8 photo-like) |
| Errors | 0 |
| Clean labels with every field as expected | 22 of 23 |
| Photo-like label fields with an acceptable result | 56 of 56 |
| False passes (a planted problem shown as Matches) | 0 |
| False fails (a Problem where none was planted) | 1 |
| Clean label fields read exactly as printed | 159 of 161 |
| Time per label (median / p95 / max) | 2.39 s / 3.35 s / 3.36 s |
| Labels checked in under 5 seconds | 31 of 31 |
| Fields to look at that were outlined on the picture | 18 of 24 |
| AI cost for this run (estimate from tokens) | $0.0219 |

Field results by kind: exact 214, extra review 1, false fail 1, review instead of fail 1.

## False fails

- chateau-landrevin-wine: bottler_name_address

## By label

| Label | Photo | Time | Result |
|---|---|---|---|
| old-tom-bourbon |  | 3.36 s | all fields as expected |
| stones-throw-gin |  | 2.05 s | all fields as expected |
| ridgewick-rye-wrong-abv |  | 2.94 s | all fields as expected |
| harborlume-rum-proof |  | 2.25 s | all fields as expected |
| copperfen-vodka-title-case-warning |  | 2.37 s | all fields as expected |
| heronmere-gin-warning-wording |  | 2.38 s | all fields as expected |
| northvale-whisky-warning-not-bold |  | 2.52 s | all fields as expected |
| saltreed-vodka-net-contents |  | 2.15 s | all fields as expected |
| chateau-landrevin-wine |  | 2.71 s | 1 false fail |
| tidewick-pale-ale |  | 2.61 s | all fields as expected |
| granitefall-bourbon-prompt-injection |  | 2.56 s | all fields as expected |
| seiran-japanese-whisky |  | 2.18 s | all fields as expected |
| kirchberger-german-lager |  | 2.49 s | all fields as expected |
| silverbirch-vodka-centiliters |  | 2.5 s | all fields as expected |
| driftwood-rum-no-warning |  | 2.13 s | all fields as expected |
| meadowvine-table-wine |  | 2.91 s | all fields as expected |
| irongate-bourbon-proof-only |  | 2.12 s | all fields as expected |
| lakemoor-lager-metric-only |  | 2.76 s | all fields as expected |
| fernhollow-gin-unauthorized-size |  | 2.1 s | all fields as expected |
| verdale-dessert-wine-no-alcohol |  | 2.1 s | all fields as expected |
| tallgrass-bourbon-two-sides |  | 2.23 s | all fields as expected |
| silvernook-whiskey-no-bottled-by |  | 2.79 s | all fields as expected |
| cerro-plateado-tequila |  | 2.37 s | all fields as expected |
| stones-throw-gin--tilted | tilted | 2.44 s | all fields as expected |
| ridgewick-rye-wrong-abv--angled | angled | 2.39 s | all fields as expected |
| heronmere-gin-warning-wording--blurry | blurry | 3.35 s | 1 review instead of fail |
| copperfen-vodka-title-case-warning--dim | dim | 2.56 s | all fields as expected |
| saltreed-vodka-net-contents--glare | glare | 2.23 s | all fields as expected |
| tidewick-pale-ale--far | far | 2.46 s | 1 extra review |
| northvale-whisky-warning-not-bold--tilted | tilted | 2.22 s | all fields as expected |
| harborlume-rum-proof--glare | glare | 2.37 s | all fields as expected |
