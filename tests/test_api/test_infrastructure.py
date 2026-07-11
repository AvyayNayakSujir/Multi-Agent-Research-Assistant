import uuid

from fastapi import Depends
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.security import verify_api_key
from app.exceptions.custom_exceptions import ToolExecutionError
from app.main import app


# Dynamically attach test endpoints to the real app instance for integration testing
@app.get("/test-custom-exception")
def route_raising_custom_exception():
    raise ToolExecutionError("Tavily lookup failed")


@app.get("/test-unhandled-exception")
def route_raising_unhandled_exception():
    raise ValueError("Something unexpected went wrong")


@app.get("/test-secured-route")
def route_secured(api_key: str = Depends(verify_api_key)):
    return {"secured": True}


client = TestClient(app, raise_server_exceptions=False)


def test_health_check_returns_request_id():
    """Verify that health check succeeds and returns a generated X-Request-ID header."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert "X-Request-ID" in response.headers
    # Verify that request ID is a valid UUID
    request_id = response.headers["X-Request-ID"]
    assert uuid.UUID(request_id)


def test_uses_provided_request_id():
    """Verify that if X-Request-ID is provided in request headers, it is returned in response."""
    test_id = str(uuid.uuid4())
    response = client.get("/health", headers={"X-Request-ID": test_id})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == test_id


def test_custom_exception_handler():
    """Verify that custom application exceptions are mapped to the correct JSON structure."""
    response = client.get("/test-custom-exception")
    assert response.status_code == 502  # Default for ToolExecutionError
    json_data = response.json()
    assert json_data["error"] == "ToolExecutionError"
    assert json_data["message"] == "Tavily lookup failed"
    assert "request_id" in json_data


def test_unhandled_exception_handler():
    """Verify that raw/unhandled exceptions return a generic 500 error page."""
    response = client.get("/test-unhandled-exception")
    assert response.status_code == 500
    json_data = response.json()
    assert json_data["error"] == "InternalServerError"
    assert (
        json_data["message"] == "An unexpected error occurred. Please contact support."
    )
    assert "request_id" in json_data


def test_secured_route_missing_api_key():
    """Verify that calling a secured route without header returns 401 UnauthorizedError."""
    response = client.get("/test-secured-route")
    assert response.status_code == 401
    json_data = response.json()
    assert json_data["error"] == "UnauthorizedError"
    assert "API Key is missing" in json_data["message"]


def test_secured_route_invalid_api_key():
    """Verify that calling a secured route with invalid key returns 401 UnauthorizedError."""
    response = client.get("/test-secured-route", headers={"X-API-Key": "wrong-key"})
    assert response.status_code == 401
    json_data = response.json()
    assert json_data["error"] == "UnauthorizedError"
    assert "Invalid API Key" in json_data["message"]


def test_secured_route_valid_api_key():
    """Verify that calling a secured route with the correct API key succeeds."""
    response = client.get(
        "/test-secured-route", headers={"X-API-Key": settings.API_KEY}
    )
    assert response.status_code == 200
    assert response.json() == {"secured": True}
