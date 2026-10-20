# Evaluation, 2026-10-20T05:10:18

Mode: the deployed app at https://ttb-label-verifier.kindmoss-39b6eae5.eastus2.azurecontainerapps.io, through its web pages. Times are single checks, one at a time, end to end from this computer: upload, reading, rules, outlines, and the page coming back. Field results are from one batch of all the labels.

Commit of this evaluation tool: `36ff5ce`. The deployed app: revision ttb-label-verifier--0000021, image f1cac8c.

## Summary

| Measure | Result |
|---|---|
| Labels | 31 (23 clean, 8 photo-like) |
| Errors | 0 |
| Clean labels with every field as expected | 23 of 23 |
| Photo-like label fields with an acceptable result | 56 of 56 |
| False passes (a planted problem shown as Matches) | 0 |
| False fails (a Problem where none was planted) | 0 |
| Time per label (median / p95 / max) | 2.7 s / 4.15 s / 4.38 s |
| Labels checked in under 5 seconds | 31 of 31 |
| Of that, time inside the app (median / p95 / max) | 2.5 s / 4.0 s / 4.2 s |
| Whole batch, upload to finished | 53.5 s |
| Fields to look at that were outlined on the picture | 16 of 22 |
| Checks where Tesseract's second reading was ready in time | 31 of 31 |

Field results by kind: exact 217.

## By label

| Label | Photo | Time | Result |
|---|---|---|---|
| old-tom-bourbon |  | 3.67 s | all fields as expected |
| stones-throw-gin |  | 3.25 s | all fields as expected |
| ridgewick-rye-wrong-abv |  | 2.78 s | all fields as expected |
| harborlume-rum-proof |  | 2.56 s | all fields as expected |
| copperfen-vodka-title-case-warning |  | 4.15 s | all fields as expected |
| heronmere-gin-warning-wording |  | 2.43 s | all fields as expected |
| northvale-whisky-warning-not-bold |  | 4.38 s | all fields as expected |
| saltreed-vodka-net-contents |  | 2.47 s | all fields as expected |
| chateau-landrevin-wine |  | 3.41 s | all fields as expected |
| tidewick-pale-ale |  | 2.69 s | all fields as expected |
| granitefall-bourbon-prompt-injection |  | 2.68 s | all fields as expected |
| seiran-japanese-whisky |  | 2.55 s | all fields as expected |
| kirchberger-german-lager |  | 2.7 s | all fields as expected |
| silverbirch-vodka-centiliters |  | 2.52 s | all fields as expected |
| driftwood-rum-no-warning |  | 3.74 s | all fields as expected |
| meadowvine-table-wine |  | 2.89 s | all fields as expected |
| irongate-bourbon-proof-only |  | 2.62 s | all fields as expected |
| lakemoor-lager-metric-only |  | 2.31 s | all fields as expected |
| fernhollow-gin-unauthorized-size |  | 2.64 s | all fields as expected |
| verdale-dessert-wine-no-alcohol |  | 2.59 s | all fields as expected |
| tallgrass-bourbon-two-sides |  | 2.74 s | all fields as expected |
| silvernook-whiskey-no-bottled-by |  | 2.59 s | all fields as expected |
| cerro-plateado-tequila |  | 3.39 s | all fields as expected |
| stones-throw-gin--tilted | tilted | 3.17 s | all fields as expected |
| ridgewick-rye-wrong-abv--angled | angled | 2.86 s | all fields as expected |
| heronmere-gin-warning-wording--blurry | blurry | 2.45 s | all fields as expected |
| copperfen-vodka-title-case-warning--dim | dim | 3.07 s | all fields as expected |
| saltreed-vodka-net-contents--glare | glare | 2.56 s | all fields as expected |
| tidewick-pale-ale--far | far | 3.37 s | all fields as expected |
| northvale-whisky-warning-not-bold--tilted | tilted | 2.37 s | all fields as expected |
| harborlume-rum-proof--glare | glare | 2.82 s | all fields as expected |

## Notes

Revision 21 adds the rule changes made for real labels and the warning's second reading by
Tesseract: in single checks it reads every picture while Claude works; in a batch it reads only
the picture with the warning, after Claude. A second batch of the same 31 labels, sent right
after this run, took 55.7 s. Before the second reading, on revision 19, the batch took 13.7 s
([evaluation-2026-10-20-deployed.md](evaluation-2026-10-20-deployed.md)). The app has one CPU, so
Tesseract's reading of 8 labels at once queues up: a batch now takes about 1.8 s a label.
