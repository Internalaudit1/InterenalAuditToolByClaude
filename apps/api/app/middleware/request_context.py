from __future__ import annotations

from time import perf_counter
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        correlation_id = request.headers.get("X-Correlation-ID", uuid4().hex)
        start = perf_counter()
        request.state.correlation_id = correlation_id
        request.state.ip_address = request.client.host if request.client else None
        request.state.user_agent = request.headers.get("User-Agent")
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        response.headers["X-Response-Time-Ms"] = str(round((perf_counter() - start) * 1000, 2))
        return response

