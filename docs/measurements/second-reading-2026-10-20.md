# The warning's second reading on real labels, 2026-10-20

72 approved labels from TTB's Public COLA Registry (the three private sets), each label's saved reading by Claude replayed with the app's own check, and Tesseract run on the picture with the warning, as in a batch. No AI request was made. Measured with `tools/second_reading.py`; only totals are published.

| What the second reading made of the warning | Labels |
|---|---|
| missing: neither pass read the warning | 29 |
| both passes read it, and agreed with the AI reader | 20 |
| missing: one pass read the warning, the other didn't | 12 |
| both passes read it; only one disagreed (taken for a misreading) | 6 |
| both passes read it, and disagreed with the AI reader | 5 |
| **All** | **72** |

## What this means

- **The second reading is missing on 41 of 72 labels (57%):** on 29 neither of Tesseract's
  passes read the warning, and on 12 only one did. Real warnings are small, sideways, curved,
  or on busy backgrounds, which Tesseract reads poorly. On those labels, a misspelling Claude
  reads as spelt correctly can't be caught.
- **On 6 labels only one pass disagreed with Claude.** The rule takes that for Tesseract
  misreading small print, so it says nothing: inconclusive.
- **On 5 labels both passes disagreed with Claude**, so the warning needed review. From the
  private results, 2 of the 5 are real misprints in the warning that Claude read spelt
  correctly; the other 3 are Tesseract reading text beside the warning into it, or misreading a
  number.
- **So the second reading gave a clear, useful answer on 22 of 72 labels**: agreement on 20,
  and 2 real misprints caught. The warning rule is not changed by this measurement.
