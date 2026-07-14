from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.logging import get_logger

logger = get_logger(__name__)


def get_api_key_or_ip(request: Request) -> str:
    """Extracts the X-API-Key header to use as the rate limiting key.

    Falls back to the remote IP address if the header is missing.
    """
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return api_key
    return get_remote_address(request)


# Create limiter instance using our custom key function
limiter = Limiter(key_func=get_api_key_or_ip)


async def rate_limit_exceeded_handler(
    request: Request, exc: RateLimitExceeded
) -> JSONResponse:
    """Custom exception handler for slowapi RateLimitExceeded exception.

    Formats the response to match the unified API error JSON structure.
    """
    request_id = getattr(request.state, "request_id", None)
    api_key = request.headers.get("X-API-Key")
    identifier = f"key: {api_key}" if api_key else f"IP: {get_remote_address(request)}"

    logger.warning(
        f"Rate limit exceeded for {identifier}. Limit: {exc.detail}",
        extra={
            "request_id": request_id,
            "rate_limit_detail": exc.detail,
        },
    )

    return JSONResponse(
        status_code=429,
        content={
            "error": "RateLimitExceeded",
            "message": f"Rate limit exceeded: {exc.detail}",
            "request_id": request_id,
        },
    )
