"""Request size limit and security headers, as plain ASGI middleware."""

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
