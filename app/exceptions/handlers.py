from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.logging import get_logger
from app.exceptions.custom_exceptions import AppBaseException

logger = get_logger("exception_handlers")


def register_exception_handlers(app: FastAPI) -> None:
    """Registers exception handlers on the FastAPI application."""

    @app.exception_handler(AppBaseException)
    async def app_base_exception_handler(
        request: Request, exc: AppBaseException
    ) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)

        # Log application exceptions as warnings since they are anticipated business errors
        logger.warning(
            f"AppBaseException caught: {exc.__class__.__name__} - {exc.message}",
            extra={
                "exception_type": exc.__class__.__name__,
                "request_id": request_id,
            },
        )

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.__class__.__name__,
                "message": exc.message,
                "request_id": request_id,
            },
        )

    @app.exception_handler(Exception)
    async def catch_all_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)

        # Log raw server exceptions with full traceback (exc_info) to console
        logger.error(
            f"Unhandled exception occurred: {str(exc)}",
            exc_info=exc,
            extra={
                "request_id": request_id,
            },
        )

        return JSONResponse(
            status_code=500,
            content={
                "error": "InternalServerError",
                "message": "An unexpected error occurred. Please contact support.",
                "request_id": request_id,
            },
        )
