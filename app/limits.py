"""Request size limit, security headers, and rate limits."""

import math
import time
from collections import deque
from datetime import UTC, datetime, timedelta

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.config import Settings

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


RECEIVING_OTHERS = (
    "The app is receiving other large uploads right now. Please try again in a few minutes."
)


class RequestSizeLimit:
    """Refuse request bodies over max_bytes, before the app reads them into memory. And
    refuse a new upload while the uploads being handled already come to max_receiving_bytes,
    since each is held in memory until its request is done."""

    def __init__(self, app: ASGIApp, max_bytes: int, max_receiving_bytes: int | None = None):
        self.app = app
        self.max_bytes = max_bytes
        self.max_receiving_bytes = max_receiving_bytes
        self.receiving = 0  # declared bytes of the requests being handled now

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
        if length is not None:
            size = int(length)
        else:  # no body, or one sent in pieces, which may be as large as allowed
            size = 0 if scope["method"] in ("GET", "HEAD") else self.max_bytes
        if self.too_busy(size):
            await self.refuse(send, 503, RECEIVING_OTHERS)
            return
        self.receiving += size
        try:
            await self.limited(scope, receive, send)
        finally:
            self.receiving -= size

    def too_busy(self, size: int) -> bool:
        """Whether a body of this size would take the uploads being handled past the cap.
        One upload alone is always let in."""
        cap = self.max_receiving_bytes
        return cap is not None and size > 0 and self.receiving > 0 and self.receiving + size > cap

    async def limited(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Pass the request on, refusing it once its body goes past max_bytes."""
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

    def current(self, visitor: str) -> deque[float]:
        """The visitor's times still inside the window."""
        now = self.clock()
        times = self.recent.setdefault(visitor, deque())
        while times and now - times[0] >= self.window_seconds:
            times.popleft()
        return times

    def has_room(self, visitor: str, count: int = 1) -> bool:
        return len(self.current(visitor)) + count <= self.limit

    def wait(self, visitor: str, count: int = 1) -> float:
        """Seconds until `count` more fit in the window: 0 if they fit now, and infinite
        if they never will."""
        times = self.current(visitor)
        over = len(times) + count - self.limit
        if over <= 0:
            return 0.0
        if over > len(times):
            return math.inf
        return times[over - 1] + self.window_seconds - self.clock()

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

    def __init__(self, limit: int, now=lambda: datetime.now(UTC)):
        self.limit = limit
        self.now = now
        self.day = now().date()
        self.used = 0

    def remaining(self) -> int:
        if self.now().date() != self.day:
            self.day, self.used = self.now().date(), 0
        return self.limit - self.used

    def seconds_to_midnight(self) -> float:
        now = self.now()
        midnight = datetime.combine(now.date() + timedelta(days=1), datetime.min.time(), UTC)
        return (midnight - now).total_seconds()

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
        now=lambda: datetime.now(UTC),
    ):
        self.checks = VisitorWindow(checks_per_visitor, check_window_seconds, clock)
        self.batches = VisitorWindow(batches_per_visitor, batch_window_seconds, clock)
        self.daily = DailyCap(labels_per_day, now)

    @classmethod
    def from_settings(cls, settings: Settings) -> "Limits":
        return cls(
            settings.checks_per_visitor,
            settings.check_window_seconds,
            settings.batches_per_visitor,
            settings.batch_window_seconds,
            settings.labels_per_day,
        )

    def take_check(self, visitor: str) -> str | None:
        """Record one single-label check if allowed. Returns None, or why not."""
        if self.daily.remaining() < 1:
            return self.daily_message()
        if not self.checks.has_room(visitor):
            minutes = round(self.checks.window_seconds / 60)
            return (
                f"You have checked {self.checks.limit} labels in the last {minutes} minutes, "
                f"which is the limit for this demo. {wait_for(self.checks.wait(visitor))}"
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
                f"today. Please send a smaller batch, or try again {self.after_midnight()}."
            )
        if not self.batches.has_room(visitor):
            minutes = round(self.batches.window_seconds / 60)
            return (
                f"You have sent {self.batches.limit} batches in the last {minutes} minutes, "
                f"which is the limit for this demo. {wait_for(self.batches.wait(visitor))}"
            )
        self.batches.record(visitor)
        self.daily.record(labels)
        return None

    def daily_message(self) -> str:
        return (
            f"This demo has reached its limit of {self.daily.limit:,} labels for today. "
            f"Please try again {self.after_midnight()}."
        )

    def after_midnight(self) -> str:
        """When the daily count starts again: "in 6 hours, after midnight UTC"."""
        return f"in {how_long(self.daily.seconds_to_midnight())}, after midnight UTC"


def how_long(seconds: float) -> str:
    """A wait in plain words, rounded up so it is never too short: "1 minute",
    "25 minutes", "6 hours"."""
    minutes = max(1, math.ceil(seconds / 60))
    if minutes == 1:
        return "1 minute"
    if minutes <= 90:
        return f"{minutes} minutes"
    return f"{math.ceil(minutes / 60)} hours"


def wait_for(seconds: float) -> str:
    if math.isinf(seconds):
        return "Please try again later."  # only when the limit is 0
    return f"Please wait {how_long(seconds)} and try again."


def visitor_id(headers: dict[str, str], client_host: str | None) -> str:
    """The visitor's address. Azure's ingress appends the real client address as the
    last X-Forwarded-For entry, so only that entry is trusted."""
    forwarded = headers.get("x-forwarded-for", "")
    if forwarded.strip():
        return forwarded.split(",")[-1].strip()
    return client_host or "unknown"
