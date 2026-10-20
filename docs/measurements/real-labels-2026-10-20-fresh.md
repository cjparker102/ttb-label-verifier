# Real labels from the COLA Registry, 2026-10-20

Approved labels from TTB's Public COLA Registry, checked in process with the app's own code. Commit: `88fc444`. Settings: `{'model': 'claude-haiku-5-5', 'thinking': 'off', 'effort': 'low', 'max_image_edge': 1568}`.

The pictures, the application data, the answer key, and the result for each label are kept private. Only these totals and the TTB IDs are published.

Accuracy is given twice, never combined. **Strict** counts the fields with one right answer, including every planted problem. **Judgment calls** count the fields where the answer key accepts two answers, such as Matches or Check this for a warning whose body text looks bold.

Some approvals carry qualifications: TTB approved the label and noted a condition, such as a statement to correct when new labels are printed. The fields each condition names were written down before the run. Conditions about things the tool doesn't check, and TTB's standard note that it didn't review type size or contrast, aren't counted.

| Measure | Result |
|---|---|
| Labels | 24 (8 distilled spirits, 8 malt beverages, 8 wine) |
| Checks | 48: each label as approved, and with one planted problem |
| Errors | 0 |
| Labels read with basic text reading | 0 |
| **Strict:** fields with one right answer, as expected | 258 of 283 |
| Strict: the others | extra review 9, false fail 10, false pass 4, review instead of fail 2 |
| **Judgment calls:** fields where two answers are right, either given | 45 of 53 |
| Judgment calls: the others | false fail 6, false pass 2 |
| Planted problems shown as Problem | 22 of 24 |
| Planted problems shown as Check this | 2 |
| Planted problems missed (shown as Matches) | 0 |
| Issues flagged on the labels as approved | 33: 12 Problem, 21 Check this |
| Of those, on a field TTB's qualifications name | 5 of 33 |
| Fields TTB's qualifications name, flagged by the tool | 5 of 6 |
| Time per check (median / p95 / max) | 2.98 s / 4.34 s / 6.57 s |
| AI cost for this run (estimate from tokens) | $0.037 |

## TTB IDs

Each can be looked up in the registry. They are listed in order of ID, not of results.

- 26001001000042
- 26002001000069
- 26002001000129
- 26002001000181
- 26002001000209
- 26002001000213
- 26002001000246
- 26004001000020
- 26004001000073
- 26005001000270
- 26005001000332
- 26005001000407
- 26005001000522
- 26005001000623
- 26006001000053
- 26006001000094
- 26006001000171
- 26008001000289
- 26013001000479
- 26014001000529
- 26098001000239
- 26106001000229
- 26111001000678
- 26117001000063

## About this run

The **fresh set**: 24 other approved labels, chosen by the same rule as the first set after the
rule changes were finished, skipping the first set's labels and companies. The answer key was
checked by Christopher against the pictures before the run, and nothing in the app was changed
after these labels were seen. So this is the honest measure. The first set's runs are in
[real-labels-2026-10-20.md](real-labels-2026-10-20.md) (before the changes) and
[real-labels-2026-10-20-tuning.md](real-labels-2026-10-20-tuning.md) (after them).

Written after the run, from the private results. No label is named.

**Planted problems.** All 24 were flagged: 22 as Problem, 2 as Check this. In 20 of them the
field was fine on the unchanged label, and 19 of those were shown as Problem.

**False passes.** 6 field results, on 3 labels, each wrong on both of its copies:

- An alcohol statement in a form TTB doesn't allow ("BY/VOL"), which TTB noted, passed the form
  check.
- A misspelt word in the warning's heading: Claude read it spelt correctly, and the second
  reading didn't run, because it finds the warning by its heading.
- A front label whose net contents contradict the back label's. Claude read the back label's,
  which is correct, and the tool never saw the other.

**What TTB noted.** TTB noted 6 conditions on things the tool checks. The tool flagged 5 of them,
4 for the reason TTB gave. The fifth, a stray letter in a warning, was shown as Check this
only because bold couldn't be confirmed; neither reading found the stray letter. The one not
flagged is the alcohol statement above. Of the 33 issues flagged on the labels as approved, 5
are on a field TTB's qualifications name.

**Warnings.** Some approved labels contain warning-text differences, including some TTB didn't
mention. Two warnings with a changed or missing word were shown as Problem. On one of them
Claude also read a misspelt word spelt correctly, and the second reading caught it: "Two readings
of the warning disagree". One warning missing its final period was shown as Check this, but
because Claude marked it hard to read, not because the period was found.

**Flagged on the labels as approved.** 33 issues: 12 Problem, 21 Check this. 19 agree with the
answer key. The other 14:

| Field | Shown, though the key disagrees | Why |
|---|---|---|
| Brand name | 4 Problem | Claude took the company or a shorter form for the brand, and the application's whole brand wasn't found elsewhere: it is in stylized lettering neither reader read. |
| Class or type | 2 Problem | Claude read a type word for the class ("Blanco"), or the words of a stacked layout in another order. |
| Net contents | 1 Problem | "1 pint (16 fl oz)" was added up to 2 pints: a bug. |
| Bottler | 1 Problem, 1 Check this | A company name with a digit in it was taken for a street address: a bug. A logo word read twice before the importer's name. |
| Alcohol content | 1 Problem | A range ("11-14%") was compared as one number. |
| Warning | 2 Check this | Text beside the warning was read into it by Tesseract, so the two readings disagreed; and a warning Claude marked hard to read. |
| Brand name (field of view) | 1 Check this | Brand, class, and alcohol read on different pictures. |
| Bottler | 1 Check this | Claude marked it hard to read. |

**Second reading and speed.** Tesseract's second reading was ready in time on 48 of 48 checks
(in process, on a laptop). 47 of 48 checks took under 5 seconds.
