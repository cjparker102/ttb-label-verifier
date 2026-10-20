# Evaluation, 2026-10-20T05:44:45

Mode: the deployed app at https://ttb-label-verifier.kindmoss-39b6eae5.eastus2.azurecontainerapps.io, through its web pages. Times are single checks, one at a time, end to end from this computer: upload, reading, rules, outlines, and the page coming back. Field results are from one batch of all the labels.

Commit of this evaluation tool: `e72cc4c`. The deployed app: revision ttb-label-verifier--0000023, image e72cc4c, 2 CPUs, 4 GiB.

## Summary

| Measure | Result |
|---|---|
| Labels | 31 (23 clean, 8 photo-like) |
| Errors | 0 |
| Clean labels with every field as expected | 23 of 23 |
| Photo-like label fields with an acceptable result | 56 of 56 |
| False passes (a planted problem shown as Matches) | 0 |
| False fails (a Problem where none was planted) | 0 |
| Time per label (median / p95 / max) | 2.88 s / 3.68 s / 4.44 s |
| Labels checked in under 5 seconds | 31 of 31 |
| Of that, time inside the app (median / p95 / max) | 2.7 s / 3.5 s / 4.3 s |
| Whole batch, upload to finished | 28.6 s |
| Fields to look at that were outlined on the picture | 17 of 24 |
| Checks where Tesseract's second reading was ready in time | 31 of 31 |

Field results by kind: exact 214, extra review 2, review instead of fail 1.

## By label

| Label | Photo | Time | Result |
|---|---|---|---|
| old-tom-bourbon |  | 3.58 s | all fields as expected |
| stones-throw-gin |  | 2.93 s | all fields as expected |
| ridgewick-rye-wrong-abv |  | 3.25 s | all fields as expected |
| harborlume-rum-proof |  | 2.55 s | all fields as expected |
| copperfen-vodka-title-case-warning |  | 3.54 s | all fields as expected |
| heronmere-gin-warning-wording |  | 2.24 s | all fields as expected |
| northvale-whisky-warning-not-bold |  | 2.68 s | all fields as expected |
| saltreed-vodka-net-contents |  | 2.7 s | all fields as expected |
| chateau-landrevin-wine |  | 4.44 s | all fields as expected |
| tidewick-pale-ale |  | 3.4 s | all fields as expected |
| granitefall-bourbon-prompt-injection |  | 2.67 s | all fields as expected |
| seiran-japanese-whisky |  | 2.8 s | all fields as expected |
| kirchberger-german-lager |  | 3.68 s | all fields as expected |
| silverbirch-vodka-centiliters |  | 2.71 s | all fields as expected |
| driftwood-rum-no-warning |  | 2.97 s | all fields as expected |
| meadowvine-table-wine |  | 2.55 s | all fields as expected |
| irongate-bourbon-proof-only |  | 2.88 s | all fields as expected |
| lakemoor-lager-metric-only |  | 2.27 s | all fields as expected |
| fernhollow-gin-unauthorized-size |  | 2.91 s | all fields as expected |
| verdale-dessert-wine-no-alcohol |  | 2.61 s | all fields as expected |
| tallgrass-bourbon-two-sides |  | 2.96 s | all fields as expected |
| silvernook-whiskey-no-bottled-by |  | 2.65 s | all fields as expected |
| cerro-plateado-tequila |  | 3.18 s | all fields as expected |
| stones-throw-gin--tilted | tilted | 2.92 s | all fields as expected |
| ridgewick-rye-wrong-abv--angled | angled | 2.75 s | all fields as expected |
| heronmere-gin-warning-wording--blurry | blurry | 2.43 s | 1 extra review, 1 review instead of fail |
| copperfen-vodka-title-case-warning--dim | dim | 2.39 s | all fields as expected |
| saltreed-vodka-net-contents--glare | glare | 2.99 s | 1 extra review |
| tidewick-pale-ale--far | far | 2.44 s | all fields as expected |
| northvale-whisky-warning-not-bold--tilted | tilted | 3.34 s | all fields as expected |
| harborlume-rum-proof--glare | glare | 3.06 s | all fields as expected |
