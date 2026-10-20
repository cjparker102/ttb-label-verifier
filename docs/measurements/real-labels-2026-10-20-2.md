# Real labels from the COLA Registry, 2026-10-20

Approved labels from TTB's Public COLA Registry, checked in process with the app's own code. Commit: `4b72296`. Settings: `{'model': 'claude-haiku-5-5', 'thinking': 'off', 'effort': 'low', 'max_image_edge': 1568}`.

The pictures, the application data, the answer key, and the result for each label are kept private. Only these totals and the TTB IDs are published.

Accuracy is given twice, never combined. **Strict** counts the fields with one right answer, including every planted problem. **Judgment calls** count the fields where the answer key accepts two answers, such as Matches or Check this for a warning whose body text looks bold.

Some approvals carry qualifications: TTB approved the label and noted a condition, such as a statement to correct when new labels are printed. The fields each condition names were written down before the run. Conditions about things the tool doesn't check, and TTB's standard note that it didn't review type size or contrast, aren't counted.

| Measure | Result |
|---|---|
| Labels | 24 (8 distilled spirits, 8 malt beverages, 8 wine) |
| Checks | 48: each label as approved, and with one planted problem |
| Errors | 0 |
| Labels read with basic text reading | 0 |
| **Strict:** fields with one right answer, as expected | 251 of 267 |
| Strict: the others | extra review 7, false fail 5, false pass 1, review instead of fail 3 |
| **Judgment calls:** fields where two answers are right, either given | 67 of 69 |
| Judgment calls: the others | false fail 2 |
| Planted problems shown as Problem | 23 of 24 |
| Planted problems shown as Check this | 1 |
| Planted problems missed (shown as Matches) | 0 |
| Issues flagged on the labels as approved | 31: 7 Problem, 24 Check this |
| Of those, on a field TTB's qualifications name | 6 of 31 |
| Fields TTB's qualifications name, flagged by the tool | 6 of 7 |
| Time per check (median / p95 / max) | 2.83 s / 4.09 s / 4.89 s |
| AI cost for this run (estimate from tokens) | $0.0391 |

## TTB IDs

Each can be looked up in the registry. They are listed in order of ID, not of results.

- 26001001000034
- 26001001000038
- 26001001000044
- 26001001000050
- 26002001000021
- 26002001000026
- 26002001000062
- 26002001000127
- 26002001000192
- 26002001000222
- 26003001000072
- 26003001000083
- 26005001000108
- 26005001000282
- 26005001000325
- 26005001000677
- 26007001000528
- 26009001000638
- 26021001000297
- 26077001000859
- 26084001000449
- 26090001000061
- 26116001000068
- 26195001000426

## About this run

The same 24 labels as [real-labels-2026-10-20.md](real-labels-2026-10-20.md), checked again
after the rules were changed because of that run: the bottler, brand, class, and net
contents comparisons, and a second reading of the warning by Tesseract. The changes were
developed against these labels, so this is the **tuning set**, and its numbers flatter the
rules. A fresh set of labels, chosen by the same rule after the changes were finished, gives
the honest number.

- Tesseract's second reading was ready in time on 48 of 48 checks (in process, on a laptop).
- The misspelt warning is now shown as Check this on both copies of its label, because the
  two readings disagree. Claude still read the word as spelt correctly, even when told to
  copy the warning letter by letter.
- The one false pass is a missing comma in a warning: Claude put it in when reading the
  planted copy. The second reading compares words, not punctuation, so it can't catch this.
- One planted problem, a different company name in the right city and state, is shown as
  Check this rather than Problem, because it may be a trade name.
