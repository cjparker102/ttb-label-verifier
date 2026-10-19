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


class RateLimiter:
    """Counts label checks per visitor over a sliding window, plus a daily total for
    the whole app. Kept in memory, which works because the app runs as one replica."""

    def __init__(
        self,
        per_visitor: int,
        window_seconds: float,
        per_day: int,
        clock=time.monotonic,
        today=lambda: datetime.now(UTC).date(),
    ):
        self.per_visitor = per_visitor
        self.window_seconds = window_seconds
        self.per_day = per_day
        self.clock = clock
        self.today = today
        self.recent: dict[str, deque[float]] = {}
        self.day = today()
        self.used_today = 0

    def take(self, visitor: str, labels: int = 1) -> str | None:
        """Record checks of `labels` labels if allowed. Returns None, or why not."""
        if self.today() != self.day:
            self.day, self.used_today = self.today(), 0
        if self.used_today + labels > self.per_day:
            return (
                f"This demo has reached its limit of {self.per_day:,} labels for today. "
                "Please try again tomorrow."
            )
        now = self.clock()
        times = self.recent.setdefault(visitor, deque())
        while times and now - times[0] >= self.window_seconds:
            times.popleft()
        if len(times) + labels > self.per_visitor:
            minutes = round(self.window_seconds / 60)
            return (
                f"You have checked {self.per_visitor} labels in the last {minutes} minutes, "
                "which is the limit for this demo. Please wait a few minutes and try again."
            )
        times.extend([now] * labels)
        self.used_today += labels
        self.forget_idle(now)
        return None

    def forget_idle(self, now: float) -> None:
        if len(self.recent) > 10_000:
            idle = [
                v for v, t in self.recent.items() if not t or now - t[-1] >= self.window_seconds
            ]
            for visitor in idle:
                del self.recent[visitor]


def visitor_id(headers: dict[str, str], client_host: str | None) -> str:
    """The visitor's address. Azure's ingress appends the real client address as the
    last X-Forwarded-For entry, so only that entry is trusted."""
    forwarded = headers.get("x-forwarded-for", "")
    if forwarded.strip():
        return forwarded.split(",")[-1].strip()
    return client_host or "unknown"
