# Real labels from the COLA Registry, 2026-10-20

Approved labels from TTB's Public COLA Registry, checked in process with the app's own code. Commit: `6530f56`. Settings: `{'model': 'claude-haiku-5-5', 'thinking': 'off', 'effort': 'low', 'max_image_edge': 1568}`.

The pictures, the application data, the answer key, and the result for each label are kept private. Only these totals and the TTB IDs are published.

Accuracy is given twice, never combined. **Strict** counts the fields with one right answer, including every planted problem. **Judgment calls** count the fields where the answer key accepts two answers, such as Matches or Check this for a warning whose body text looks bold.

Some approvals carry qualifications: TTB approved the label and noted a condition, such as a statement to correct when new labels are printed. The fields each condition names were written down before the run. Conditions about things the tool doesn't check, and TTB's standard note that it didn't review type size or contrast, aren't counted.

| Measure | Result |
|---|---|
| Labels | 24 (8 distilled spirits, 8 malt beverages, 8 wine) |
| Checks | 48: each label as approved, and with one planted problem |
| Errors | 0 |
| Labels read with basic text reading | 0 |
| **Strict:** fields with one right answer, as expected | 252 of 274 |
| Strict: the others | extra review 11, false fail 11 |
| **Judgment calls:** fields where two answers are right, either given | 50 of 62 |
| Judgment calls: the others | false fail 10, false pass 2 |
| Planted problems shown as Problem | 24 of 24 |
| Planted problems shown as Check this | 0 |
| Planted problems missed (shown as Matches) | 0 |
| Planted problems detected, shown as Problem | 24 |
| Planted problems detected, shown as Check this | 0 |
| Planted problems shown as Problem for another reason | 0 |
| Planted problems sent to review for another reason | 0 |
| Planted problems missed, shown as Matches | 0 |
| Issues flagged on the labels as approved | 34: 13 Problem, 21 Check this |
| Of those, on a field TTB's qualifications name | 1 of 34 |
| Fields TTB's qualifications name, flagged by the tool | 1 of 2 |
| Time per check (median / p95 / max) | 2.98 s / 5.93 s / 7.18 s |
| AI cost for this run (estimate from tokens) | $0.0466 |

## Planted problems, label by label

Each label was checked a second time with one field of its application changed to a wrong value. These made-up problems are published label by label; the real labels' own results are not. **Detected** means the field's comparison with the application raised it; **another reason** means the field was flagged for something else, such as print too hard to read.

| TTB ID | Field changed | Result | How |
|---|---|---|---|
| 26002001000040 | Country of origin | Problem | detected, shown as Problem |
| 26002001000137 | Alcohol content | Problem | detected, shown as Problem |
| 26003001000018 | Net contents | Problem | detected, shown as Problem |
| 26003001000020 | Brand name | Problem | detected, shown as Problem |
| 26003001000061 | Class or type | Problem | detected, shown as Problem |
| 26003001000081 | Alcohol content | Problem | detected, shown as Problem |
| 26004001000022 | Brand name | Problem | detected, shown as Problem |
| 26004001000069 | Net contents | Problem | detected, shown as Problem |
| 26005001000084 | Alcohol content | Problem | detected, shown as Problem |
| 26005001000291 | Class or type | Problem | detected, shown as Problem |
| 26005001000368 | Alcohol content | Problem | detected, shown as Problem |
| 26005001000374 | Net contents | Problem | detected, shown as Problem |
| 26005001000488 | Brand name | Problem | detected, shown as Problem |
| 26005001000635 | Class or type | Problem | detected, shown as Problem |
| 26006001000250 | Country of origin | Problem | detected, shown as Problem |
| 26006001000418 | Alcohol content | Problem | detected, shown as Problem |
| 26007001000327 | Bottler or importer | Problem | detected, shown as Problem |
| 26008001000610 | Net contents | Problem | detected, shown as Problem |
| 26008001000748 | Alcohol content | Problem | detected, shown as Problem |
| 26014001000128 | Bottler or importer | Problem | detected, shown as Problem |
| 26014001000694 | Country of origin | Problem | detected, shown as Problem |
| 26015001000895 | Brand name | Problem | detected, shown as Problem |
| 26020001000392 | Class or type | Problem | detected, shown as Problem |
| 26036001000391 | Brand name | Problem | detected, shown as Problem |

## TTB IDs

Each can be looked up in the registry. They are listed in order of ID, not of results.

- 26002001000040
- 26002001000137
- 26003001000018
- 26003001000020
- 26003001000061
- 26003001000081
- 26004001000022
- 26004001000069
- 26005001000084
- 26005001000291
- 26005001000368
- 26005001000374
- 26005001000488
- 26005001000635
- 26006001000250
- 26006001000418
- 26007001000327
- 26008001000610
- 26008001000748
- 26014001000128
- 26014001000694
- 26015001000895
- 26020001000392
- 26036001000391
