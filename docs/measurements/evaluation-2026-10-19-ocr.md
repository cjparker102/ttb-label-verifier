# Evaluation, 2026-10-19T09:25:08

Mode: in process, reader `ocr`, settings `{'model': 'claude-haiku-5-5', 'thinking': 'off', 'effort': 'low', 'max_image_edge': 1568}`.

Commit: `dbc98dc-dirty`.

## Summary

| Measure | Result |
|---|---|
| Labels | 31 (23 clean, 8 photo-like) |
| Errors | 0 |
| Clean labels with every field as expected | 1 of 23 |
| Photo-like label fields with an acceptable result | 56 of 56 |
| False passes (a planted problem shown as Matches) | 0 |
| False fails (a Problem where none was planted) | 0 |
| Time per label (median / p95 / max) | 0.45 s / 0.68 s / 0.8 s |
| Labels checked in under 5 seconds | 31 of 31 |
| Fields to look at that were outlined on the picture | 44 of 44 |
| Labels read with basic text reading | 31 |

Field results by kind: exact 158, extra review 43, review instead of fail 16.

## By label

| Label | Photo | Time | Result |
|---|---|---|---|
| old-tom-bourbon |  | 0.8 s | 1 extra review |
| stones-throw-gin |  | 0.47 s | 2 extra review |
| ridgewick-rye-wrong-abv |  | 0.46 s | 1 review instead of fail, 1 extra review |
| harborlume-rum-proof |  | 0.46 s | 1 review instead of fail, 1 extra review |
| copperfen-vodka-title-case-warning |  | 0.46 s | 1 review instead of fail |
| heronmere-gin-warning-wording |  | 0.45 s | 1 review instead of fail |
| northvale-whisky-warning-not-bold |  | 0.48 s | all fields as expected |
| saltreed-vodka-net-contents |  | 0.45 s | 1 review instead of fail, 1 extra review |
| chateau-landrevin-wine |  | 0.51 s | 1 extra review |
| tidewick-pale-ale |  | 0.45 s | 1 extra review |
| granitefall-bourbon-prompt-injection |  | 0.54 s | 1 review instead of fail, 1 extra review |
| seiran-japanese-whisky |  | 0.46 s | 1 extra review |
| kirchberger-german-lager |  | 0.49 s | 2 extra review |
| silverbirch-vodka-centiliters |  | 0.44 s | 1 extra review |
| driftwood-rum-no-warning |  | 0.32 s | 1 review instead of fail |
| meadowvine-table-wine |  | 0.45 s | 2 extra review |
| irongate-bourbon-proof-only |  | 0.45 s | 1 review instead of fail, 2 extra review |
| lakemoor-lager-metric-only |  | 0.44 s | 1 review instead of fail, 1 extra review |
| fernhollow-gin-unauthorized-size |  | 0.45 s | 1 review instead of fail, 1 extra review |
| verdale-dessert-wine-no-alcohol |  | 0.46 s | 1 review instead of fail, 2 extra review |
| tallgrass-bourbon-two-sides |  | 0.68 s | 1 extra review |
| silvernook-whiskey-no-bottled-by |  | 0.45 s | 1 extra review |
| cerro-plateado-tequila |  | 0.48 s | 1 extra review |
| stones-throw-gin--tilted | tilted | 0.46 s | 5 extra review |
| ridgewick-rye-wrong-abv--angled | angled | 0.44 s | 1 review instead of fail, 1 extra review |
| heronmere-gin-warning-wording--blurry | blurry | 0.25 s | 3 extra review, 1 review instead of fail |
| copperfen-vodka-title-case-warning--dim | dim | 0.45 s | 1 review instead of fail |
| saltreed-vodka-net-contents--glare | glare | 0.42 s | 3 extra review, 1 review instead of fail |
| tidewick-pale-ale--far | far | 0.2 s | 2 extra review |
| northvale-whisky-warning-not-bold--tilted | tilted | 0.51 s | 3 extra review |
| harborlume-rum-proof--glare | glare | 0.43 s | 1 review instead of fail, 2 extra review |
