# A code-side bold check, measured, 2026-10-20

The stroke thickness of the warning's heading against the warning's words after it, measured on the picture where Tesseract found both. The check would add Check this when Claude calls the heading bold but it measures less than clearly heavier; when Claude doesn't call it bold, it is Check this already. Each label's saved reading by Claude was used; no AI request was made. Real labels: the four private sets as approved, with the headings the answer keys say aren't bold. Measured with `tools/heading_weight.py`; only totals are published.

- Samples, not bold: 2 labels; Claude called 1 bold; 2 measured, whatever Claude said (lowest: 1.07, 1.09)
- Samples, bold: 28 labels; Claude called 28 bold; 25 measured, whatever Claude said (lowest: 1.40, 1.55, 1.56, 1.56, 1.57, 1.66)
- Real, not bold: 6 labels; Claude called 0 bold; 4 measured, whatever Claude said (lowest: 0.96, 0.97, 0.98, 1.11)
- Real, bold: 90 labels; Claude called 71 bold; 65 measured, whatever Claude said (lowest: 0.82, 0.87, 0.88, 0.90, 0.93, 0.93)

Labels the check would send to review. With a bold heading, each one is a false alarm about the heading. For real labels, "wrong" counts those whose answer key says Matches for the warning, so the flag would make the result wrong; the others' keys accept Check this for another reason, such as a small picture.

| Clearly heavier means | Print at least | Samples, not bold (2) | Samples, bold (28) | Real, not bold (6) | Real, bold (90) |
|---|---|---|---|---|---|
| 1 times | any size | 0 | 0 | 0 | 6 (3 wrong) |
| 1 times | 14 px | 0 | 0 | 0 | 4 (1 wrong) |
| 1.05 times | any size | 0 | 0 | 0 | 7 (3 wrong) |
| 1.05 times | 14 px | 0 | 0 | 0 | 4 (1 wrong) |
| 1.1 times | any size | 1 | 0 | 0 | 11 (4 wrong) |
| 1.1 times | 14 px | 1 | 0 | 0 | 6 (2 wrong) |
| 1.15 times | any size | 1 | 0 | 0 | 13 (5 wrong) |
| 1.15 times | 14 px | 1 | 0 | 0 | 7 (2 wrong) |
| 1.2 times | any size | 1 | 0 | 0 | 18 (7 wrong) |
| 1.2 times | 14 px | 1 | 0 | 0 | 11 (4 wrong) |
