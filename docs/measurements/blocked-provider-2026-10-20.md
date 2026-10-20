# A blocked AI provider, 2026-10-20

A single check of the sample `old-tom-bourbon`, in process on a laptop, with the app's client pointed at an address that can't be reached. Connect timeout 3 s, reading deadline 8 s, one retry, a second request after 4 s. Measured with `tools/blocked_provider.py`.

| Provider address | Read by | Check time, each run | Median |
|---|---|---|---|
| dropped (no answer, as a firewall that drops traffic) | ocr | 8.5 s, 8.5 s, 8.5 s | 8.5 s |
| refused (the connection is turned away at once) | ocr | 0.9 s, 0.9 s, 0.9 s | 0.9 s |

When the traffic is dropped, the first request's connection times out after 3 seconds and is
tried once more; a second request is sent after 4 seconds; and at the 8-second deadline the
check gives up on Claude and reads the label with Tesseract, which takes about half a second
here. When the connection is refused, both tries fail at once.
