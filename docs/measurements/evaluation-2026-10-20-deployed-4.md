# Evaluation, 2026-10-20T09:01:40

Mode: the deployed app at https://ttb-label-verifier.kindmoss-39b6eae5.eastus2.azurecontainerapps.io, through its web pages. Times are single checks, one at a time, end to end from this computer: upload, reading, rules, outlines, and the page coming back. Field results are from one batch of all the labels.

Commit of this evaluation tool: `77dd73a`. The deployed app: revision ttb-label-verifier--0000025, image 77dd73a, 2 CPUs, 4 GiB.

## Summary

| Measure | Result |
|---|---|
| Labels | 31 (23 clean, 8 photo-like) |
| Errors | 0 |
| Clean labels with every field as expected | 22 of 23 |
| Photo-like label fields with an acceptable result | 56 of 56 |
| False passes (a planted problem shown as Matches) | 1 |
| False fails (a Problem where none was planted) | 0 |
| Time per label (median / p95 / max) | 2.89 s / 3.85 s / 4.83 s |
| Labels checked in under 5 seconds | 31 of 31 |
| Of that, time inside the app (median / p95 / max) | 2.7 s / 3.5 s / 4.6 s |
| Whole batch, upload to finished | 30.3 s |
| Fields to look at that were outlined on the picture | 17 of 22 |
| Checks where Tesseract's second reading was ready in time | 31 of 31 |

Field results by kind: exact 215, false pass 1, review instead of fail 1.

## False passes

- northvale-whisky-warning-not-bold: government_warning

## By label

| Label | Photo | Time | Result |
|---|---|---|---|
| old-tom-bourbon |  | 3.85 s | all fields as expected |
| stones-throw-gin |  | 2.74 s | all fields as expected |
| ridgewick-rye-wrong-abv |  | 2.77 s | all fields as expected |
| harborlume-rum-proof |  | 2.87 s | all fields as expected |
| copperfen-vodka-title-case-warning |  | 3.18 s | all fields as expected |
| heronmere-gin-warning-wording |  | 2.78 s | all fields as expected |
| northvale-whisky-warning-not-bold |  | 3.17 s | 1 false pass |
| saltreed-vodka-net-contents |  | 2.89 s | all fields as expected |
| chateau-landrevin-wine |  | 2.93 s | all fields as expected |
| tidewick-pale-ale |  | 2.62 s | all fields as expected |
| granitefall-bourbon-prompt-injection |  | 3.22 s | all fields as expected |
| seiran-japanese-whisky |  | 2.82 s | all fields as expected |
| kirchberger-german-lager |  | 3.13 s | all fields as expected |
| silverbirch-vodka-centiliters |  | 3.38 s | all fields as expected |
| driftwood-rum-no-warning |  | 2.54 s | all fields as expected |
| meadowvine-table-wine |  | 2.37 s | all fields as expected |
| irongate-bourbon-proof-only |  | 2.64 s | all fields as expected |
| lakemoor-lager-metric-only |  | 2.96 s | all fields as expected |
| fernhollow-gin-unauthorized-size |  | 3.0 s | all fields as expected |
| verdale-dessert-wine-no-alcohol |  | 3.05 s | all fields as expected |
| tallgrass-bourbon-two-sides |  | 3.18 s | all fields as expected |
| silvernook-whiskey-no-bottled-by |  | 2.97 s | all fields as expected |
| cerro-plateado-tequila |  | 2.77 s | all fields as expected |
| stones-throw-gin--tilted | tilted | 4.83 s | all fields as expected |
| ridgewick-rye-wrong-abv--angled | angled | 2.92 s | all fields as expected |
| heronmere-gin-warning-wording--blurry | blurry | 3.3 s | 1 review instead of fail |
| copperfen-vodka-title-case-warning--dim | dim | 2.64 s | all fields as expected |
| saltreed-vodka-net-contents--glare | glare | 2.53 s | all fields as expected |
| tidewick-pale-ale--far | far | 2.55 s | all fields as expected |
| northvale-whisky-warning-not-bold--tilted | tilted | 2.87 s | all fields as expected |
| harborlume-rum-proof--glare | glare | 2.79 s | all fields as expected |

## Notes

Revision 25: everything changed overnight after ChatGPT's review, on 2 CPUs. The false pass is
the sample whose warning heading isn't bold, read as bold in the batch; see "Bold type" in
[APPROACH.md](../APPROACH.md).
