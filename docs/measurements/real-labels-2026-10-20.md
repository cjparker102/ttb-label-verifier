# Real labels from the COLA Registry, 2026-10-20

Approved labels from TTB's Public COLA Registry, checked in process with the app's own code. Commit: `0fd8770`. Settings: `{'model': 'claude-haiku-5-5', 'thinking': 'off', 'effort': 'low', 'max_image_edge': 1568}`.

The pictures, the application data, the answer key, and the result for each label are kept private. Only these totals and the TTB IDs are published.

Accuracy is given twice, never combined. **Strict** counts the fields with one right answer, including every planted problem. **Judgment calls** count the fields where the answer key accepts two answers, such as Matches or Check this for a warning whose body text looks bold.

Some approvals carry qualifications: TTB approved the label and noted a condition, such as a statement to correct when new labels are printed. The fields each condition names were written down before the run. Conditions about things the tool doesn't check, and TTB's standard note that it didn't review type size or contrast, aren't counted.

| Measure | Result |
|---|---|
| Labels | 24 (8 distilled spirits, 8 malt beverages, 8 wine) |
| Checks | 48: each label as approved, and with one planted problem |
| Errors | 0 |
| Labels read with basic text reading | 0 |
| **Strict:** fields with one right answer, as expected | 205 of 267 |
| Strict: the others | extra review 11, false fail 48, false pass 1, review instead of fail 2 |
| **Judgment calls:** fields where two answers are right, either given | 39 of 69 |
| Judgment calls: the others | false fail 30 |
| Planted problems shown as Problem | 24 of 24 |
| Planted problems shown as Check this | 0 |
| Planted problems missed (shown as Matches) | 0 |
| Issues flagged on the labels as approved | 62: 43 Problem, 19 Check this |
| Of those, on a field TTB's qualifications name | 6 of 62 |
| Fields TTB's qualifications name, flagged by the tool | 6 of 7 |
| Time per check (median / p95 / max) | 2.88 s / 3.68 s / 9.95 s |
| AI cost for this run (estimate from tokens) | $0.0378 |

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

Written after the run, from the private results. No label is named.

**Planted problems.** All 24 were shown as Problem. In 6 of them the field was already
flagged on the unchanged label (5 as Problem, 1 as Check this), so those show little. In the
other 18, where the field came out fine on the unchanged label, all 18 were caught.

**What TTB noted.** Of the 62 issues flagged on the labels as approved, 6 are the same issue
TTB noted in its qualifications on the approval, for the same reason: an alcohol statement not
in an allowed form (2), net contents in milliliters only on a malt beverage, a punctuation
difference in the warning (2), and brand, class, and alcohol content not in one field of view.
TTB noted 7 conditions on things the tool checks. The one not flagged is a reminder that net
contents must be shown on the label or the bottle; the tool found it there.

The fields were written down before the run, and one was corrected after it: the
field-of-view condition had been left out as something the tool doesn't check, but the tool
does check it, for spirits. Before the correction the counts were 5 of 62 and 5 of 6.

**False alarms.** 47 of the 62 issues flagged on the labels as approved disagree with the
answer key, 41 of them as Problem:

| Field | Flagged, though fine | Why |
|---|---|---|
| Bottler or importer | 21 | Compared word for word. Real labels leave out "LLC" or "Inc.", spell the state out, add a street and ZIP code, name the producer before the importer, or use a trade name. |
| Brand name | 13 | Claude read a fanciful name or the company name as the brand (9); the label's brand was shorter or longer than the registry's (3); the field-of-view check (1). |
| Class or type | 8 | The label prints other words with the class, such as an appellation, a fanciful name, or "Premium", and the whole phrase was compared. |
| Net contents | 4 | Keg labels list several sizes to tick, and they were added up (2); a size given twice, in two forms, was added up (1); "GALS" wasn't read as gallons (1). |
| Government warning | 1 | Bold couldn't be confirmed (Check this). |

**Missed.** One label's warning has a misspelt word. Claude read it as spelt correctly both
times, so it was shown as Check this (for a spacing difference), not Problem. On the planted
copy of another label, Claude read the same picture again and put in a comma that is missing
from the warning, so the warning was shown as Matches: the one false pass. On the label as
approved, the missing comma was found.
