from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable

from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.observability.metrics import http_requests_total

_PUBLIC_PATHS = frozenset(
    {
        "/health",
        "/health/live",
        "/health/ready",
        "/metrics",
        "/docs",
        "/redoc",
        "/openapi.json",
    }
)


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        rid = request.headers.get("x-request-id") or str(uuid.uuid4())
        request.state.request_id = rid
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        status = response.status_code
        status_class = f"{status // 100}xx"
        route = request.scope.get("route")
        path_template = getattr(route, "path", request.url.path)
        http_requests_total.labels(
            method=request.method,
            path_template=path_template,
            status_class=status_class,
        ).inc()
        return response


class ApiKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if settings.api_key is None:
            return await call_next(request)
        if request.url.path in _PUBLIC_PATHS:
            return await call_next(request)
        provided = request.headers.get("x-api-key")
        expected = settings.api_key.get_secret_value()
        if not provided or provided != expected:
            raise HTTPException(status_code=401, detail="Invalid or missing API key")
        return await call_next(request)
