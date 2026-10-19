"""Request size limit, security headers, and rate limits."""

import time
from collections import deque
from datetime import UTC, datetime

from starlette.types import ASGIApp, Message, Receive, Scope, Send

SECURITY_HEADERS = [
    (
        b"content-security-policy",
        b"default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; "
        b"form-action 'self'; frame-ancestors 'none'; base-uri 'none'",
    ),
    (b"x-content-type-options", b"nosniff"),
    (b"referrer-policy", b"no-referrer"),
    (b"x-frame-options", b"DENY"),
    # Results show label details, so browsers and proxies must not keep a copy.
    (b"cache-control", b"no-store"),
]


class SecurityHeaders:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                message["headers"] = [*message.get("headers", []), *SECURITY_HEADERS]
            await send(message)

        await self.app(scope, receive, send_with_headers)


class TooLarge(Exception):
    pass


class RequestSizeLimit:
    """Refuse request bodies over max_bytes, before the app reads them into memory."""

    def __init__(self, app: ASGIApp, max_bytes: int):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        length = dict(scope["headers"]).get(b"content-length")
        if length is not None:
            if not length.isdigit():
                await self.refuse(send, 400, "The request was not understood.")
                return
            if int(length) > self.max_bytes:
                await self.refuse(send, 413, self.too_large_message())
                return

        received = 0
        started = False

        async def counting_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    raise TooLarge
            return message

        async def tracking_send(message: Message) -> None:
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            await self.app(scope, counting_receive, tracking_send)
        except TooLarge:
            if not started:
                await self.refuse(send, 413, self.too_large_message())

    def too_large_message(self) -> str:
        return f"This upload is too large. The limit is {self.max_bytes // (1024 * 1024)} MB."

    async def refuse(self, send: Send, status: int, text: str) -> None:
        body = (
            "<!doctype html><html lang=en><meta charset=utf-8>"
            f"<title>TTB Label Verifier</title><p>{text}</p><p><a href=/>Go back</a></p></html>"
        ).encode()
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [
                    (b"content-type", b"text/html; charset=utf-8"),
                    (b"content-length", str(len(body)).encode()),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})


class VisitorWindow:
    """How many times each visitor did something within a sliding time window."""

    def __init__(self, limit: int, window_seconds: float, clock=time.monotonic):
        self.limit = limit
        self.window_seconds = window_seconds
        self.clock = clock
        self.recent: dict[str, deque[float]] = {}

    def has_room(self, visitor: str, count: int = 1) -> bool:
        now = self.clock()
        times = self.recent.setdefault(visitor, deque())
        while times and now - times[0] >= self.window_seconds:
            times.popleft()
        return len(times) + count <= self.limit

    def record(self, visitor: str, count: int = 1) -> None:
        now = self.clock()
        self.recent.setdefault(visitor, deque()).extend([now] * count)
        if len(self.recent) > 10_000:  # forget visitors who have gone quiet
            for idle in [
                v for v, t in self.recent.items() if not t or now - t[-1] >= self.window_seconds
            ]:
                del self.recent[idle]


class DailyCap:
    """Labels checked today by everyone together. Resets at midnight UTC."""

    def __init__(self, limit: int, today=lambda: datetime.now(UTC).date()):
        self.limit = limit
        self.today = today
        self.day = today()
        self.used = 0

    def remaining(self) -> int:
        if self.today() != self.day:
            self.day, self.used = self.today(), 0
        return self.limit - self.used

    def record(self, labels: int) -> None:
        self.remaining()
        self.used += labels


class Limits:
    """All the app's usage limits. Kept in memory, which works because the app runs as
    one replica. A check or batch is counted only if every limit that applies has room."""

    def __init__(
        self,
        checks_per_visitor: int,
        check_window_seconds: float,
        batches_per_visitor: int,
        batch_window_seconds: float,
        labels_per_day: int,
        clock=time.monotonic,
        today=lambda: datetime.now(UTC).date(),
    ):
        self.checks = VisitorWindow(checks_per_visitor, check_window_seconds, clock)
        self.batches = VisitorWindow(batches_per_visitor, batch_window_seconds, clock)
        self.daily = DailyCap(labels_per_day, today)

    def take_check(self, visitor: str) -> str | None:
        """Record one single-label check if allowed. Returns None, or why not."""
        if self.daily.remaining() < 1:
            return self.daily_message()
        if not self.checks.has_room(visitor):
            minutes = round(self.checks.window_seconds / 60)
            return (
                f"You have checked {self.checks.limit} labels in the last {minutes} minutes, "
                "which is the limit for this demo. Please wait a few minutes and try again."
            )
        self.checks.record(visitor)
        self.daily.record(1)
        return None

    def take_batch(self, visitor: str, labels: int) -> str | None:
        """Record a batch of this many labels if allowed. Returns None, or why not."""
        left = self.daily.remaining()
        if left < 1:
            return self.daily_message()
        if labels > left:
            return (
                f"This batch has {labels} labels, but this demo can check only {left} more "
                "today. Please send a smaller batch, or try again tomorrow."
            )
        if not self.batches.has_room(visitor):
            minutes = round(self.batches.window_seconds / 60)
            return (
                f"You have sent {self.batches.limit} batches in the last {minutes} minutes, "
                "which is the limit for this demo. Please try again later."
            )
        self.batches.record(visitor)
        self.daily.record(labels)
        return None

    def daily_message(self) -> str:
        return (
            f"This demo has reached its limit of {self.daily.limit:,} labels for today. "
            "Please try again tomorrow."
        )


def visitor_id(headers: dict[str, str], client_host: str | None) -> str:
    """The visitor's address. Azure's ingress appends the real client address as the
    last X-Forwarded-For entry, so only that entry is trusted."""
    forwarded = headers.get("x-forwarded-for", "")
    if forwarded.strip():
        return forwarded.split(",")[-1].strip()
    return client_host or "unknown"
