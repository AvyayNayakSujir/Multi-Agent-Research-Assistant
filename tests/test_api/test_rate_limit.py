from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.security import verify_api_key
from app.main import app
from app.middleware.rate_limit import limiter

client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def reset_rate_limits():
    """Fixture to reset the rate limiter state before each test case."""
    limiter.reset()
    yield
    limiter.reset()


@patch("app.api.v1.routes.research.run_workflow")
def test_rate_limiting_success_up_to_limit(mock_run_workflow):
    """Verify requests with valid API key succeed up to the limit (10/minute)."""
    mock_run_workflow.return_value = {
        "query": "FastAPI",
        "reader_output": [],
        "draft": "Draft",
        "approved": True,
        "iteration_count": 1,
        "max_iterations": 3,
    }

    payload = {"query": "FastAPI Rate Limit", "max_iterations": 3}
    headers = {"X-API-Key": settings.API_KEY}

    # Make 10 valid requests (up to the limit of 10/minute)
    for _ in range(10):
        response = client.post("/api/v1/research", json=payload, headers=headers)
        assert response.status_code == 200

    assert mock_run_workflow.call_count == 10


@patch("app.api.v1.routes.research.run_workflow")
def test_rate_limiting_exceeded_error_shape(mock_run_workflow):
    """Verify that exceeding the rate limit returns a 429 with custom JSON error shape."""
    mock_run_workflow.return_value = {
        "approved": True,
        "iteration_count": 1,
    }

    payload = {"query": "FastAPI Rate Limit Exceeded", "max_iterations": 3}
    headers = {"X-API-Key": settings.API_KEY}

    # First 10 requests succeed
    for _ in range(10):
        response = client.post("/api/v1/research", json=payload, headers=headers)
        assert response.status_code == 200

    # The 11th request must be blocked and return 429
    response = client.post("/api/v1/research", json=payload, headers=headers)
    assert response.status_code == 429

    json_data = response.json()
    assert json_data["error"] == "RateLimitExceeded"
    assert "Rate limit exceeded" in json_data["message"]
    assert "request_id" in json_data

    # Verify that run_workflow was only executed for the 10 successful requests
    assert mock_run_workflow.call_count == 10


@patch("app.api.v1.routes.research.run_workflow")
def test_rate_limiting_independent_keys(mock_run_workflow):
    """Verify that different API keys have independent rate limits."""
    mock_run_workflow.return_value = {
        "approved": True,
        "iteration_count": 1,
    }

    payload = {
        "query": "FastAPI Rate Limit Multi-Key",
        "max_iterations": 3,
    }

    key_a = "key-alpha"
    key_b = "key-beta"

    # Use FastAPI dependency_overrides to temporarily bypass verification on alpha and beta keys
    app.dependency_overrides[verify_api_key] = lambda: True
    try:
        # Exhaust Key A (10 calls)
        for _ in range(10):
            response = client.post(
                "/api/v1/research",
                json=payload,
                headers={"X-API-Key": key_a},
            )
            assert response.status_code == 200

        # 11th call for Key A is blocked (429)
        response = client.post(
            "/api/v1/research", json=payload, headers={"X-API-Key": key_a}
        )
        assert response.status_code == 429

        # Key B should still succeed since its limit is independent
        response = client.post(
            "/api/v1/research", json=payload, headers={"X-API-Key": key_b}
        )
        assert response.status_code == 200
    finally:
        app.dependency_overrides.clear()


def test_health_check_unaffected_by_limits():
    """Verify that the /health endpoint is completely unaffected by rate limiting."""
    # Call /health 15 times consecutively; all must return 200
    for _ in range(15):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
