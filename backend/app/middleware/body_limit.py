"""ASGI middleware: reject requests whose body exceeds a configured byte limit.

Streaming requests are usually small (a few messages), but we don't want a malicious or
broken client to upload gigabytes through the gateway and cost us memory.
"""
from __future__ import annotations

from starlette.types import ASGIApp, Message, Receive, Scope, Send


class BodySizeLimitMiddleware:
    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or self.max_bytes <= 0:
            await self.app(scope, receive, send)
            return

        # Fast path: trust Content-Length if the client sent it.
        for name, value in scope.get("headers", []):
            if name == b"content-length":
                try:
                    if int(value) > self.max_bytes:
                        await self._reject(send)
                        return
                except ValueError:
                    pass
                break

        # Slow path: count bytes as they arrive.
        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    raise _RequestTooLargeError
            return message

        try:
            await self.app(scope, limited_receive, send)
        except _RequestTooLargeError:
            await self._reject(send)

    async def _reject(self, send: Send) -> None:
        await send(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": [(b"content-type", b"application/json")],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": b'{"error":{"code":"payload_too_large","message":"Request body exceeds limit."}}',
            }
        )


class _RequestTooLargeError(Exception):
    pass
