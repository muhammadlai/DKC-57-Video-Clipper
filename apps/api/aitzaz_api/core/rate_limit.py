"""Rate limiting foundation (Phase 1: in-process sliding window).

Designed to be swapped for a Redis-backed limiter in a later phase without
changing call sites: the middleware only depends on a ``RateLimiter``
protocol. Redis is intentionally optional in Phase 1.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from aitzaz_api.core.errors import error_payload

EXEMPT_PATHS = {"/", "/api/health", "/api/v1/health", "/docs", "/redoc", "/openapi.json"}


class SlidingWindowLimiter:
    """Thread-safe-enough in-memory limiter (GIL-atomic deque ops)."""

    def __init__(self, per_minute: int) -> None:
        self.per_minute = per_minute
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str) -> bool:
        """Return True when the request is allowed."""
        now = time.monotonic()
        window_start = now - 60.0
        hits = self._hits[key]
        while hits and hits[0] < window_start:
            hits.popleft()
        if len(hits) >= self.per_minute:
            return False
        hits.append(now)
        return True

    def reset(self) -> None:
        self._hits.clear()


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, enabled: bool, per_minute: int) -> None:
        super().__init__(app)
        self.enabled = enabled
        self.limiter = SlidingWindowLimiter(per_minute)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if (
            not self.enabled
            or request.method == "OPTIONS"
            or request.url.path in EXEMPT_PATHS
        ):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        if not self.limiter.check(client_ip):
            retry_after = 60
            response = JSONResponse(
                status_code=429,
                content=error_payload(
                    "rate_limited",
                    "Too many requests. Please slow down and try again shortly.",
                ),
                headers={"Retry-After": str(retry_after)},
            )
            return response
        return await call_next(request)


def make_limiter(settings) -> RateLimitMiddleware.__init__ | None:  # pragma: no cover
    """Factory kept for clarity in app startup."""
    return None
