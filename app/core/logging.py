import contextvars
import json
import logging
import sys
from datetime import datetime, UTC
from typing import Any

from app.core.config import settings

# Thread-safe ContextVar to store current request ID
request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)


class JSONFormatter(logging.Formatter):
    """Custom formatter to output logs in structured JSON format."""

    def format(self, record: logging.LogRecord) -> str:
        # Standard fields
        log_data: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }

        # Include request_id if set in the current execution context
        req_id = request_id_var.get()
        if req_id:
            log_data["request_id"] = req_id

        # Include traceback details if an exception is present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Include any custom context passed via 'extra' dictionary
        extra_fields = {
            k: v
            for k, v in record.__dict__.items()
            if k
            not in {
                "args",
                "asctime",
                "created",
                "exc_info",
                "exc_text",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "msg",
                "name",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "stack_info",
                "thread",
                "threadName",
            }
        }
        if extra_fields:
            # Merge extra fields directly
            log_data.update(extra_fields)

        return json.dumps(log_data)


def setup_logging() -> None:
    """Configures structured JSON logging globally."""
    # Resolve log level
    level_name = settings.LOG_LEVEL or "INFO"
    level = getattr(logging, level_name.upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Clear existing default handlers
    for idx, handler in enumerate(root_logger.handlers[:]):
        root_logger.removeHandler(handler)

    # Create console handler with JSON formatter
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(console_handler)


def get_logger(name: str) -> logging.Logger:
    """Helper function to retrieve a configured logger."""
    return logging.getLogger(name)
