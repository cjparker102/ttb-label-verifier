# Evaluation, 2026-10-20T14:23:59

Mode: the deployed app at https://ttb-label-verifier.kindmoss-39b6eae5.eastus2.azurecontainerapps.io, through its web pages. Times are single checks, one at a time, end to end from this computer: upload, reading, rules, outlines, and the page coming back. Field results are from one batch of all the labels.

Commit of this evaluation tool: `71177c1`. The deployed app: revision ttb-label-verifier--0000026, image 71177c1, 2 CPUs, 4 GiB.

## Summary

| Measure | Result |
|---|---|
| Labels | 32 (24 clean, 8 photo-like) |
| Errors | 0 |
| Clean labels with every field as expected | 23 of 24 |
| Photo-like label fields with an acceptable result | 56 of 56 |
| False passes (a planted problem shown as Matches) | 0 |
| False fails (a Problem where none was planted) | 0 |
| Time per label (median / p95 / max) | 2.85 s / 3.95 s / 5.84 s |
| Labels checked in under 5 seconds | 31 of 32 |
| Of that, time inside the app (median / p95 / max) | 2.65 s / 3.7 s / 5.7 s |
| Whole batch, upload to finished | 31.9 s |
| Fields to look at that were outlined on the picture | 17 of 23 |
| Checks where Tesseract's second reading was ready in time | 32 of 32 |

Field results by kind: exact 221, extra review 1, note difference 1, review instead of fail 1.

## By label

| Label | Photo | Time | Result |
|---|---|---|---|
| old-tom-bourbon |  | 3.73 s | all fields as expected |
| stones-throw-gin |  | 2.93 s | all fields as expected |
| ridgewick-rye-wrong-abv |  | 2.84 s | all fields as expected |
| harborlume-rum-proof |  | 3.78 s | all fields as expected |
| copperfen-vodka-title-case-warning |  | 2.77 s | all fields as expected |
| heronmere-gin-warning-wording |  | 5.84 s | all fields as expected |
| northvale-whisky-warning-not-bold |  | 2.79 s | all fields as expected |
| saltreed-vodka-net-contents |  | 3.04 s | all fields as expected |
| chateau-landrevin-wine |  | 2.69 s | all fields as expected |
| tidewick-pale-ale |  | 2.66 s | all fields as expected |
| granitefall-bourbon-prompt-injection |  | 2.64 s | all fields as expected |
| seiran-japanese-whisky |  | 2.95 s | all fields as expected |
| kirchberger-german-lager |  | 2.88 s | all fields as expected |
| silverbirch-vodka-centiliters |  | 2.77 s | all fields as expected |
| driftwood-rum-no-warning |  | 2.3 s | all fields as expected |
| meadowvine-table-wine |  | 2.99 s | all fields as expected |
| irongate-bourbon-proof-only |  | 2.7 s | all fields as expected |
| lakemoor-lager-metric-only |  | 2.96 s | all fields as expected |
| fernhollow-gin-unauthorized-size |  | 2.66 s | all fields as expected |
| verdale-dessert-wine-no-alcohol |  | 3.08 s | all fields as expected |
| tallgrass-bourbon-two-sides |  | 3.08 s | all fields as expected |
| silvernook-whiskey-no-bottled-by |  | 2.86 s | all fields as expected |
| cerro-plateado-tequila |  | 2.77 s | all fields as expected |
| vesperly-wine-specialty |  | 3.95 s | 1 note difference |
| stones-throw-gin--tilted | tilted | 2.66 s | all fields as expected |
| ridgewick-rye-wrong-abv--angled | angled | 2.67 s | all fields as expected |
| heronmere-gin-warning-wording--blurry | blurry | 2.73 s | 1 review instead of fail |
| copperfen-vodka-title-case-warning--dim | dim | 2.65 s | all fields as expected |
| saltreed-vodka-net-contents--glare | glare | 2.94 s | all fields as expected |
| tidewick-pale-ale--far | far | 3.09 s | 1 extra review |
| northvale-whisky-warning-not-bold--tilted | tilted | 3.25 s | all fields as expected |
| harborlume-rum-proof--glare | glare | 2.78 s | all fields as expected |
