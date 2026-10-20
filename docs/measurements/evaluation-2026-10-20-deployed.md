# Evaluation, 2026-10-20T01:01:02

Mode: the deployed app at https://ttb-label-verifier.kindmoss-39b6eae5.eastus2.azurecontainerapps.io, through its web pages. Times are single checks, one at a time, end to end from this computer: upload, reading, rules, outlines, and the page coming back. Field results are from one batch of all the labels.

Commit of this evaluation tool: `ee5ecb0`. The deployed app: revision ttb-label-verifier--0000019, image `ee5ecb0`.

## Summary

| Measure | Result |
|---|---|
| Labels | 31 (23 clean, 8 photo-like) |
| Errors | 0 |
| Clean labels with every field as expected | 23 of 23 |
| Photo-like label fields with an acceptable result | 56 of 56 |
| False passes (a planted problem shown as Matches) | 0 |
| False fails (a Problem where none was planted) | 0 |
| Time per label (median / p95 / max) | 2.51 s / 4.44 s / 4.62 s |
| Labels checked in under 5 seconds | 31 of 31 |
| Of that, time inside the app (median / p95 / max) | 2.3 s / 4.3 s / 4.5 s |
| Whole batch, upload to finished | 13.7 s |
| Fields to look at that were outlined on the picture | 17 of 22 |

Field results by kind: exact 217.

## By label

| Label | Photo | Time | Result |
|---|---|---|---|
| old-tom-bourbon |  | 3.69 s | all fields as expected |
| stones-throw-gin |  | 4.62 s | all fields as expected |
| ridgewick-rye-wrong-abv |  | 3.1 s | all fields as expected |
| harborlume-rum-proof |  | 2.34 s | all fields as expected |
| copperfen-vodka-title-case-warning |  | 4.44 s | all fields as expected |
| heronmere-gin-warning-wording |  | 2.19 s | all fields as expected |
| northvale-whisky-warning-not-bold |  | 2.55 s | all fields as expected |
| saltreed-vodka-net-contents |  | 2.25 s | all fields as expected |
| chateau-landrevin-wine |  | 2.41 s | all fields as expected |
| tidewick-pale-ale |  | 2.33 s | all fields as expected |
| granitefall-bourbon-prompt-injection |  | 2.63 s | all fields as expected |
| seiran-japanese-whisky |  | 2.63 s | all fields as expected |
| kirchberger-german-lager |  | 2.44 s | all fields as expected |
| silverbirch-vodka-centiliters |  | 2.29 s | all fields as expected |
| driftwood-rum-no-warning |  | 2.87 s | all fields as expected |
| meadowvine-table-wine |  | 2.66 s | all fields as expected |
| irongate-bourbon-proof-only |  | 2.32 s | all fields as expected |
| lakemoor-lager-metric-only |  | 2.51 s | all fields as expected |
| fernhollow-gin-unauthorized-size |  | 2.94 s | all fields as expected |
| verdale-dessert-wine-no-alcohol |  | 2.26 s | all fields as expected |
| tallgrass-bourbon-two-sides |  | 2.77 s | all fields as expected |
| silvernook-whiskey-no-bottled-by |  | 2.19 s | all fields as expected |
| cerro-plateado-tequila |  | 2.51 s | all fields as expected |
| stones-throw-gin--tilted | tilted | 2.97 s | all fields as expected |
| ridgewick-rye-wrong-abv--angled | angled | 2.29 s | all fields as expected |
| heronmere-gin-warning-wording--blurry | blurry | 2.92 s | all fields as expected |
| copperfen-vodka-title-case-warning--dim | dim | 2.47 s | all fields as expected |
| saltreed-vodka-net-contents--glare | glare | 2.44 s | all fields as expected |
| tidewick-pale-ale--far | far | 2.15 s | all fields as expected |
| northvale-whisky-warning-not-bold--tilted | tilted | 2.98 s | all fields as expected |
| harborlume-rum-proof--glare | glare | 2.35 s | all fields as expected |
