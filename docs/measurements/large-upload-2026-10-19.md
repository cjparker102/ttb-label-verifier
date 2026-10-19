# Large upload on the deployed app, 2026-10-19

Azure doesn't document a request size limit for Container Apps ingress, so the largest batch
the app accepts (200 MB of files plus the spreadsheet) was sent to the live app.

## What was sent

- `samples/applications.csv` (31 rows)
- One ZIP file of 199.5 MB, stored without compression: the 33 sample label pictures plus five
  files of random bytes (`filler/scan-0.dat` to `scan-4.dat`, about 40 MB each), so the
  upload was near the limit.

Sent with curl from a home connection to revision `ttb-label-verifier--0000012` (image
`7f94e72`, 1 vCPU, 2 GiB). The app had no API key set, so it read every label with basic text
reading (Tesseract). No AI calls were made.

## Results

| Measure | Result |
|---|---|
| Request size | 209,201,268 bytes |
| Response | `303 See Other` to the batch page, from the app (not refused by Azure) |
| Upload and unpacking time | 13.1 s (about 16 MB/s upload) |
| Labels checked | 31 of 31, in about 35 s |
| Files not used | 5: the five filler files, each listed as "Not a picture or PDF this app can read" |
| Excel download | 200, 18,567 bytes |

## Something to note

Each label's time in this batch was long for basic text reading: median 8.1 s, slowest
15.2 s, against under 1 s for a single check. The batch reads 8 labels at once, which suits
Claude (it waits on the network), but Tesseract uses the CPU, and the app has one. So 8 OCR
runs shared one CPU, and each took about 8 times longer. The batch as a whole was not
slower. With the API key set, Claude reads the labels and this doesn't apply.
