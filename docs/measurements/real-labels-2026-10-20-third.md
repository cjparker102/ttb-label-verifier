# Real labels from the COLA Registry, 2026-10-20

Approved labels from TTB's Public COLA Registry, checked in process with the app's own code. Commit: `e54a509`. Settings: `{'model': 'claude-haiku-5-5', 'thinking': 'off', 'effort': 'low', 'max_image_edge': 1568}`.

The pictures, the application data, the answer key, and the result for each label are kept private. Only these totals and the TTB IDs are published.

Accuracy is given twice, never combined. **Strict** counts the fields with one right answer, including every planted problem. **Judgment calls** count the fields where the answer key accepts two answers, such as Matches or Check this for a warning whose body text looks bold.

Some approvals carry qualifications: TTB approved the label and noted a condition, such as a statement to correct when new labels are printed. The fields each condition names were written down before the run. Conditions about things the tool doesn't check, and TTB's standard note that it didn't review type size or contrast, aren't counted.

| Measure | Result |
|---|---|
| Labels | 24 (8 distilled spirits, 8 malt beverages, 8 wine) |
| Checks | 48: each label as approved, and with one planted problem |
| Errors | 0 |
| Labels read with basic text reading | 0 |
| **Strict:** fields with one right answer, as expected | 256 of 280 |
| Strict: the others | extra review 13, false fail 10, review instead of fail 1 |
| **Judgment calls:** fields where two answers are right, either given | 50 of 56 |
| Judgment calls: the others | false fail 6 |
| Planted problems shown as Problem | 23 of 24 |
| Planted problems shown as Check this | 1 |
| Planted problems missed (shown as Matches) | 0 |
| Issues flagged on the labels as approved | 31: 9 Problem, 22 Check this |
| Of those, on a field TTB's qualifications name | 2 of 31 |
| Fields TTB's qualifications name, flagged by the tool | 2 of 2 |
| Time per check (median / p95 / max) | 2.85 s / 3.54 s / 4.04 s |
| AI cost for this run (estimate from tokens) | $0.0382 |

## TTB IDs

Each can be looked up in the registry. They are listed in order of ID, not of results.

- 26001001000002
- 26001001000022
- 26002001000034
- 26002001000035
- 26002001000073
- 26002001000167
- 26002001000171
- 26002001000233
- 26003001000031
- 26004001000035
- 26004001000067
- 26005001000057
- 26005001000416
- 26005001000621
- 26006001000149
- 26006001000608
- 26007001000289
- 26007001000749
- 26008001000089
- 26008001000199
- 26008001000664
- 26014001000719
- 26015001000998
- 26034001000607

## About this run

The **third set**: 24 other approved labels, chosen by the same rule after the last rule
changes (the two fixes that followed the fresh set), skipping both earlier sets' labels and
companies. The answer key was checked by Christopher against the pictures before the run, and
nothing in the app was changed after these labels were seen. This is the honest measure. The
earlier runs: [first set](real-labels-2026-10-20.md),
[tuning set after the changes](real-labels-2026-10-20-tuning.md),
[fresh set](real-labels-2026-10-20-fresh.md).

Written after the run, from the private results. No label is named.

**Planted problems.** All 24 were flagged: 23 as Problem, 1 as Check this, because Claude marked
that label's bottler statement hard to read. In 22 of them the field was fine on the unchanged
label, and all 22 were shown as Problem.

**False passes.** None.

**What TTB noted.** TTB noted 2 conditions on things the tool checks, both errors in the
warning, and the tool flagged both: one for its missing final period, and one because its
heading's bold couldn't be confirmed, which is what TTB asked to fix. Of the 31 issues flagged
on the labels as approved, 2 are on a field TTB's qualifications name.

**Warnings.** Some approved labels contain warning-text differences that TTB didn't mention.
The tool flagged a space before the heading's colon (on 2 labels) and a missing final period as
Check this. It missed one: square brackets around the statement numbers, which Claude read as
parentheses; that warning was shown as Check this only because bold couldn't be confirmed. The
alcohol form check for spirits, changed after the fresh set, flagged one statement without
"by" or a slash as Check this. The second reading disagreed with Claude on 2 labels, both times
because Tesseract read text beside the warning or misread a number; both warnings needed review
anyway.

**Flagged on the labels as approved.** 31 issues: 9 Problem, 22 Check this. 16 agree with the
answer key. The other 15:

| Field | Shown, though the key disagrees | Why |
|---|---|---|
| Brand name | 3 Problem | Claude took a fanciful name or the company for the brand, and the application's brand wasn't found elsewhere: it is under 6 letters, so not looked for; written as one word on the label and two in the registry; or split across a banner and a line. |
| Net contents | 2 Problem | "1 pint (16 fl oz)" added up to 2 pints: the bug the fresh set found, not fixed. |
| Country of origin | 2 Problem | The country appears only inside the bottler statement ("bottled in Scotland", a brewer's address in France), and Claude reported no country statement. |
| Class or type | 1 Problem | Claude read a type word for the class ("Añejo"). |
| Government warning | 1 Problem | Claude read the line after the warning ("NOT FOR UNDER AGE.") into it. |
| Government warning | 3 Check this | Claude marked small sideways print hard to read, or bold couldn't be confirmed. |
| Bottler | 2 Check this | Claude marked small sideways print hard to read. |
| Brand name (field of view) | 1 Check this | Brand, class, and alcohol read on different pictures. |

**Speed.** 48 of 48 checks under 5 seconds (median 2.85 s, slowest 4.04 s). Tesseract's second
reading was ready in time on 48 of 48 (in process, on a laptop).

**After this run.** The "1 pint (16 fl oz)" bug was fixed: the same amount in two units now
counts once. These numbers were measured before the fix.

## Planted problems, label by label

Each label was checked a second time with one field of its application changed to a wrong value. These made-up problems are published label by label; the real labels' own results are not. **Detected** means the field's comparison with the application raised it; **another reason** means the field was flagged for something else, such as print too hard to read.

| TTB ID | Field changed | Result | How |
|---|---|---|---|
| 26001001000002 | Country of origin | Problem | detected, shown as Problem |
| 26001001000022 | Alcohol content | Problem | detected, shown as Problem |
| 26002001000034 | Brand name | Problem | detected, shown as Problem |
| 26002001000035 | Net contents | Problem | detected, shown as Problem |
| 26002001000073 | Class or type | Problem | detected, shown as Problem |
| 26002001000167 | Alcohol content | Problem | detected, shown as Problem |
| 26002001000171 | Brand name | Problem | detected, shown as Problem |
| 26002001000233 | Alcohol content | Problem | detected, shown as Problem |
| 26003001000031 | Class or type | Problem | detected, shown as Problem |
| 26004001000035 | Net contents | Problem | detected, shown as Problem |
| 26004001000067 | Brand name | Problem | detected, shown as Problem |
| 26005001000057 | Alcohol content | Problem | detected, shown as Problem |
| 26005001000416 | Class or type | Problem | detected, shown as Problem |
| 26005001000621 | Net contents | Problem | detected, shown as Problem |
| 26006001000149 | Country of origin | Problem | detected, shown as Problem |
| 26006001000608 | Alcohol content | Problem | detected, shown as Problem |
| 26007001000289 | Bottler or importer | Problem | detected, shown as Problem |
| 26007001000749 | Brand name | Problem | detected, shown as Problem |
| 26008001000089 | Country of origin | Problem | shown as Problem for another reason |
| 26008001000199 | Alcohol content | Problem | detected, shown as Problem |
| 26008001000664 | Class or type | Problem | detected, shown as Problem |
| 26014001000719 | Net contents | Problem | detected, shown as Problem |
| 26015001000998 | Brand name | Problem | detected, shown as Problem |
| 26034001000607 | Bottler or importer | Check this | sent to review for another reason |

How each planted problem was caught was worked out on Oct 20 after the run, by replaying the
saved readings through the code that ran (commit `e54a509`): the replay gave the same result as
the run for every field of all 48 checks.
