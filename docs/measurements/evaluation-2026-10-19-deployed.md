# Evaluation, 2026-10-19T18:47:47

Mode: the deployed app at https://ttb-label-verifier.kindmoss-39b6eae5.eastus2.azurecontainerapps.io, through its web pages. Times are single checks, one at a time, end to end from this computer: upload, reading, rules, outlines, and the page coming back. Field results are from one batch of all the labels.

Commit of this evaluation tool: `6490d46`. The deployed app: revision ttb-label-verifier--0000017, image `223172b`.

## Summary

| Measure | Result |
|---|---|
| Labels | 31 (23 clean, 8 photo-like) |
| Errors | 0 |
| Clean labels with every field as expected | 23 of 23 |
| Photo-like label fields with an acceptable result | 56 of 56 |
| False passes (a planted problem shown as Matches) | 0 |
| False fails (a Problem where none was planted) | 0 |
| Time per label (median / p95 / max) | 2.95 s / 4.65 s / 8.79 s |
| Labels checked in under 5 seconds | 30 of 31 |
| Of that, time inside the app (median / p95 / max) | 2.8 s / 4.5 s / 8.6 s |
| Whole batch, upload to finished | 16.1 s |
| Fields to look at that were outlined on the picture | 17 of 22 |

Field results by kind: exact 217.

## By label

| Label | Photo | Time | Result |
|---|---|---|---|
| old-tom-bourbon |  | 3.27 s | all fields as expected |
| stones-throw-gin |  | 3.51 s | all fields as expected |
| ridgewick-rye-wrong-abv |  | 3.07 s | all fields as expected |
| harborlume-rum-proof |  | 2.6 s | all fields as expected |
| copperfen-vodka-title-case-warning |  | 3.2 s | all fields as expected |
| heronmere-gin-warning-wording |  | 4.65 s | all fields as expected |
| northvale-whisky-warning-not-bold |  | 3.95 s | all fields as expected |
| saltreed-vodka-net-contents |  | 2.31 s | all fields as expected |
| chateau-landrevin-wine |  | 2.44 s | all fields as expected |
| tidewick-pale-ale |  | 3.15 s | all fields as expected |
| granitefall-bourbon-prompt-injection |  | 2.88 s | all fields as expected |
| seiran-japanese-whisky |  | 2.62 s | all fields as expected |
| kirchberger-german-lager |  | 2.38 s | all fields as expected |
| silverbirch-vodka-centiliters |  | 2.36 s | all fields as expected |
| driftwood-rum-no-warning |  | 2.64 s | all fields as expected |
| meadowvine-table-wine |  | 2.33 s | all fields as expected |
| irongate-bourbon-proof-only |  | 2.62 s | all fields as expected |
| lakemoor-lager-metric-only |  | 3.06 s | all fields as expected |
| fernhollow-gin-unauthorized-size |  | 2.74 s | all fields as expected |
| verdale-dessert-wine-no-alcohol |  | 2.5 s | all fields as expected |
| tallgrass-bourbon-two-sides |  | 2.69 s | all fields as expected |
| silvernook-whiskey-no-bottled-by |  | 3.89 s | all fields as expected |
| cerro-plateado-tequila |  | 3.32 s | all fields as expected |
| stones-throw-gin--tilted | tilted | 3.14 s | all fields as expected |
| ridgewick-rye-wrong-abv--angled | angled | 2.62 s | all fields as expected |
| heronmere-gin-warning-wording--blurry | blurry | 2.97 s | all fields as expected |
| copperfen-vodka-title-case-warning--dim | dim | 8.79 s | all fields as expected |
| saltreed-vodka-net-contents--glare | glare | 2.61 s | all fields as expected |
| tidewick-pale-ale--far | far | 2.95 s | all fields as expected |
| northvale-whisky-warning-not-bold--tilted | tilted | 3.54 s | all fields as expected |
| harborlume-rum-proof--glare | glare | 3.1 s | all fields as expected |
