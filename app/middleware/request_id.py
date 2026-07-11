import uuid

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.logging import request_id_var


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware that manages unique request identifiers (X-Request-ID).

    WARNING: Starlette's BaseHTTPMiddleware runs the generator of streaming responses
    in a separate task context. If streaming (e.g. Server-Sent Events / SSE) is used
    later for agent progress updates, BaseHTTPMiddleware may block, buffer, or cause issues
    with the streams. Consider migrating to pure ASGI middleware if streaming is introduced.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = str(uuid.uuid4())

        request.state.request_id = request_id

        # Set contextvar and ensure hygiene via token reset in try/finally
        token = request_id_var.set(request_id)
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)

        response.headers["X-Request-ID"] = request_id
        return response
