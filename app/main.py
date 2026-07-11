from fastapi import FastAPI

from app.core.logging import setup_logging
from app.exceptions.handlers import register_exception_handlers
from app.middleware.logging_middleware import LoggingMiddleware
from app.middleware.request_id import RequestIDMiddleware

# Setup logging before instantiating the FastAPI application
setup_logging()

app = FastAPI(
    title="Multi-Agent AI Research Assistant API",
    version="0.1.0",
)

# Register exception handlers
register_exception_handlers(app)

# Register middlewares.
# Starlette/FastAPI executes middlewares in the reverse order of declaration.
# Therefore, RequestIDMiddleware (added second) executes outer/before LoggingMiddleware (added first)
# on the request path, ensuring the request ID is available before request logging starts.
app.add_middleware(LoggingMiddleware)
app.add_middleware(RequestIDMiddleware)


@app.get("/health")
def health_check():
    """Health check endpoint. Unauthenticated and open to public."""
    return {"status": "ok"}
