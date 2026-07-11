from fastapi import Header

from app.core.config import settings
from app.exceptions.custom_exceptions import UnauthorizedError


async def verify_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> str:
    """Verifies the X-API-Key header against configured settings.

    Raises UnauthorizedError (status 401) if the key is missing or invalid.
    """
    if not x_api_key:
        raise UnauthorizedError("API Key is missing")

    if x_api_key != settings.API_KEY:
        raise UnauthorizedError("Invalid API Key")

    return x_api_key
