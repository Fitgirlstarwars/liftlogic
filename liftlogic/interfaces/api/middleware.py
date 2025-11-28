"""
API Middleware - Request/response processing.

Provides:
- Request ID tracking
- Response latency measurement
- Error handling with taxonomy codes
- Rate limiting
"""

from __future__ import annotations

import logging
import time
import uuid
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from liftlogic.config.errors import ErrorCode, LiftLogicError

logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach request ID for tracing across logs and responses."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        # Store in request state for access in handlers
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        return response


class LatencyMiddleware(BaseHTTPMiddleware):
    """Track and log request latency."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        start_time = time.perf_counter()

        response = await call_next(request)

        duration_ms = (time.perf_counter() - start_time) * 1000
        response.headers["X-Response-Time-Ms"] = f"{duration_ms:.2f}"

        # Log request with latency
        request_id = getattr(request.state, "request_id", "unknown")
        logger.info(
            "%s %s status=%d latency_ms=%.2f request_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            request_id,
        )

        return response


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Convert LiftLogicError exceptions to structured JSON responses."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        try:
            return await call_next(request)
        except LiftLogicError as e:
            request_id = getattr(request.state, "request_id", "unknown")
            logger.error(
                "LiftLogicError: %s request_id=%s details=%s",
                e.message,
                request_id,
                e.details,
            )
            return JSONResponse(
                status_code=_error_code_to_status(e.code),
                content={
                    "error": e.to_dict(),
                    "request_id": request_id,
                },
            )
        except Exception as e:
            request_id = getattr(request.state, "request_id", "unknown")
            logger.exception("Unhandled error: %s request_id=%s", str(e), request_id)
            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "code": ErrorCode.INTERNAL_ERROR.value,
                        "message": "Internal server error",
                        "details": {},
                    },
                    "request_id": request_id,
                },
            )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiting per client IP."""

    def __init__(self, app: ASGIApp, requests_per_minute: int = 60) -> None:
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.buckets: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"window": 0, "tokens": 0}
        )

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # Skip rate limiting for health checks
        if request.url.path == "/health":
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window = int(now // 60)  # 1-minute windows

        bucket = self.buckets[client_ip]

        # Reset bucket if new window
        if bucket["window"] != window:
            bucket["window"] = window
            bucket["tokens"] = self.requests_per_minute

        if bucket["tokens"] <= 0:
            request_id = getattr(request.state, "request_id", "unknown")
            logger.warning(
                "Rate limit exceeded for %s request_id=%s",
                client_ip,
                request_id,
            )
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": ErrorCode.SECURITY_RATE_LIMITED.value,
                        "message": "Too many requests. Please retry after 60 seconds.",
                        "details": {"retry_after": 60},
                    },
                    "request_id": request_id,
                },
                headers={"Retry-After": "60"},
            )

        bucket["tokens"] -= 1

        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(bucket["tokens"])
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)

        return response


def _error_code_to_status(code: ErrorCode) -> int:
    """Map error codes to HTTP status codes."""
    mapping = {
        # 400 Bad Request
        ErrorCode.EXTRACTION_INVALID_PDF: 400,
        ErrorCode.SEARCH_INVALID_QUERY: 400,
        ErrorCode.DIAGNOSIS_INVALID_CODE: 400,
        ErrorCode.VALIDATION_ERROR: 400,
        ErrorCode.KNOWLEDGE_INVALID_EDGE: 400,
        # 401 Unauthorized
        ErrorCode.SECURITY_UNAUTHORIZED: 401,
        ErrorCode.LLM_AUTH_FAILED: 401,
        # 403 Forbidden
        ErrorCode.SECURITY_FORBIDDEN: 403,
        # 404 Not Found
        ErrorCode.NOT_FOUND: 404,
        ErrorCode.KNOWLEDGE_NODE_NOT_FOUND: 404,
        ErrorCode.SEARCH_NO_RESULTS: 404,
        # 408 Timeout
        ErrorCode.EXTRACTION_TIMEOUT: 408,
        # 429 Rate Limited
        ErrorCode.SECURITY_RATE_LIMITED: 429,
        ErrorCode.LLM_RATE_LIMITED: 429,
        # 503 Service Unavailable
        ErrorCode.LLM_UNAVAILABLE: 503,
        ErrorCode.SEARCH_INDEX_UNAVAILABLE: 503,
        ErrorCode.KNOWLEDGE_GRAPH_UNAVAILABLE: 503,
        ErrorCode.STORAGE_CONNECTION_FAILED: 503,
    }
    return mapping.get(code, 500)
