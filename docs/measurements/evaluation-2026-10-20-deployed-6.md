# Evaluation, 2026-10-20T19:50:12

Mode: the deployed app at https://ttb-label-verifier.kindmoss-39b6eae5.eastus2.azurecontainerapps.io, through its web pages. Times are single checks, one at a time, end to end from this computer: upload, reading, rules, outlines, and the page coming back. Field results are from one batch of all the labels.

Commit of this evaluation tool: `1f7ef3c`. The deployed app: revision ttb-label-verifier--0000027, image 1f7ef3c, 2 CPUs, 4 GiB.

## Summary

| Measure | Result |
|---|---|
| Labels | 32 (24 clean, 8 photo-like) |
| Errors | 0 |
| Clean labels with every field as expected | 23 of 24 |
| Photo-like label fields with an acceptable result | 56 of 56 |
| False passes (a planted problem shown as Matches) | 0 |
| False fails (a Problem where none was planted) | 0 |
| Time per label (median / p95 / max) | 2.88 s / 4.31 s / 4.7 s |
| Labels checked in under 5 seconds | 32 of 32 |
| Of that, time inside the app (median / p95 / max) | 2.7 s / 4.1 s / 4.5 s |
| Whole batch, upload to finished | 30.1 s |
| Fields to look at that were outlined on the picture | 17 of 22 |
| Checks where Tesseract's second reading was ready in time | 32 of 32 |

Field results by kind: exact 223, note difference 1.

## By label

| Label | Photo | Time | Result |
|---|---|---|---|
| old-tom-bourbon |  | 3.11 s | all fields as expected |
| stones-throw-gin |  | 3.16 s | all fields as expected |
| ridgewick-rye-wrong-abv |  | 2.75 s | all fields as expected |
| harborlume-rum-proof |  | 2.68 s | all fields as expected |
| copperfen-vodka-title-case-warning |  | 3.14 s | all fields as expected |
| heronmere-gin-warning-wording |  | 2.9 s | all fields as expected |
| northvale-whisky-warning-not-bold |  | 3.07 s | all fields as expected |
| saltreed-vodka-net-contents |  | 4.7 s | all fields as expected |
| chateau-landrevin-wine |  | 4.31 s | all fields as expected |
| tidewick-pale-ale |  | 2.97 s | all fields as expected |
| granitefall-bourbon-prompt-injection |  | 2.68 s | all fields as expected |
| seiran-japanese-whisky |  | 2.67 s | all fields as expected |
| kirchberger-german-lager |  | 3.04 s | all fields as expected |
| silverbirch-vodka-centiliters |  | 2.65 s | all fields as expected |
| driftwood-rum-no-warning |  | 2.87 s | all fields as expected |
| meadowvine-table-wine |  | 3.17 s | all fields as expected |
| irongate-bourbon-proof-only |  | 2.66 s | all fields as expected |
| lakemoor-lager-metric-only |  | 3.15 s | all fields as expected |
| fernhollow-gin-unauthorized-size |  | 2.79 s | all fields as expected |
| verdale-dessert-wine-no-alcohol |  | 2.9 s | all fields as expected |
| tallgrass-bourbon-two-sides |  | 3.04 s | all fields as expected |
| silvernook-whiskey-no-bottled-by |  | 2.86 s | all fields as expected |
| cerro-plateado-tequila |  | 2.73 s | all fields as expected |
| vesperly-wine-specialty |  | 3.33 s | 1 note difference |
| stones-throw-gin--tilted | tilted | 2.65 s | all fields as expected |
| ridgewick-rye-wrong-abv--angled | angled | 2.77 s | all fields as expected |
| heronmere-gin-warning-wording--blurry | blurry | 3.38 s | all fields as expected |
| copperfen-vodka-title-case-warning--dim | dim | 2.24 s | all fields as expected |
| saltreed-vodka-net-contents--glare | glare | 2.87 s | all fields as expected |
| tidewick-pale-ale--far | far | 2.75 s | all fields as expected |
| northvale-whisky-warning-not-bold--tilted | tilted | 3.09 s | all fields as expected |
| harborlume-rum-proof--glare | glare | 2.6 s | all fields as expected |
