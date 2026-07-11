import time

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.logging import get_logger

logger = get_logger("request_logger")


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware that logs the details of every HTTP request, including performance latency.

    WARNING: Starlette's BaseHTTPMiddleware runs the generator of streaming responses
    in a separate task context. If streaming (e.g. Server-Sent Events / SSE) is used
    later for agent progress updates, BaseHTTPMiddleware may block, buffer, or cause issues
    with the streams. Consider migrating to pure ASGI middleware if streaming is introduced.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        start_time = time.perf_counter()
        response = None
        try:
            response = await call_next(request)
            return response
        finally:
            latency_ms = (time.perf_counter() - start_time) * 1000
            status_code = response.status_code if response else 500
            request_id = getattr(request.state, "request_id", None)

            # Log request details in structured format
            logger.info(
                f"{request.method} {request.url.path} - {status_code} - {latency_ms:.2f}ms",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code,
                    "latency_ms": round(latency_ms, 2),
                    "request_id": request_id,
                },
            )
