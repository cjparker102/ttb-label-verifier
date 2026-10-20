# Single-check time on the deployed app, with slow answers asked for again, 2026-10-20

Since revision `ttb-label-verifier--0000019` (image `ee5ecb0`), a single check that has no
answer from Claude after 4 seconds sends the same request again, and uses whichever answer
comes first. This note measures single checks on that revision, the same way as on Oct 19
([live-single-check-2026-10-19.md](live-single-check-2026-10-19.md)): from a home
connection in the US, one check at a time, warm app, sample labels as drawn.

- **The evaluation run** (`tools/evaluate.py --url`): every sample once, 31 checks, then
  the batch. Full results: [evaluation-2026-10-20-deployed.md](evaluation-2026-10-20-deployed.md).
- **Two more passes** (`tools/time_live.py --sample all --runs 2`): every sample twice more,
  62 checks, right after.

## Results

| Single checks | Oct 19, before (31) | Oct 20, evaluation run (31) | Oct 20, all (93) |
|---|---|---|---|
| End to end: median / p95 / slowest | 2.95 s / 4.65 s / 8.79 s | 2.51 s / 4.44 s / 4.62 s | 2.54 s / 3.17 s / 4.62 s |
| Inside the app: median / p95 / slowest | 2.8 s / 4.5 s / 8.6 s | 2.3 s / 4.3 s / 4.5 s | 2.3 s / 3.0 s / 4.5 s |
| Under 5 seconds, end to end | 30 of 31 | 31 of 31 | 93 of 93 |
| Asked again (no answer after 4 s) | not built | 2 | 2 |

p95 is the nearest-rank value, so it is a time that was really measured: the 30th of 31, or
the 89th of 93. All 93 checks were read by Claude. In the evaluation run every field result
was as expected (217 of 217), and the batch of 31 took 13.7 s.

## What the second request did

The app logs each time it asks again, and which request answered first. In the 93 checks it
asked again twice, both in the evaluation run, and both times the first request still
answered first:

```
04:59:33 UTC  No answer after 4 s, so the label was read again. The first request answered first, after 4.3 s.
04:59:43 UTC  No answer after 4 s, so the label was read again. The first request answered first, after 4.1 s.
```

So the better times on Oct 20 are not the second request's doing. Claude was simply quicker
that day: no answer took longer than 4.5 s inside the app, while on Oct 19 one took 8.6 s. The
case the second request is for, an answer that takes 8 seconds or more, didn't happen in
these 93 checks, so how much it helps then is not measured yet.

What was measured is the cost: 2 extra requests in 93 checks, about 2% more. No other
warnings or errors were logged.

## Cost of these runs

About 126 requests to Claude: 93 single checks, 31 batch labels, and the 2 extra requests.
At about 0.07 cents a label, roughly 9 cents.
