from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.config import settings
from app.exceptions.custom_exceptions import ToolExecutionError
from app.main import app

client = TestClient(app, raise_server_exceptions=False)


@patch("app.api.v1.routes.research.run_workflow")
def test_research_route_success(mock_run_workflow):
    """Verify that a valid request with correct API key returns 200 and matches the expected response shape."""
    mock_run_workflow.return_value = {
        "query": "FastAPI Async",
        "research_sources": [{"url": "https://raw.com", "title": "Raw"}],
        "reader_output": [
            {
                "url": "https://example.com/a",
                "title": "Title A",
                "relevant_content": "Extremely detailed content that should be stripped",
            }
        ],
        "draft": "Initial draft of async FastAPI report.",
        "critique_feedback": "Looks good.",
        "approved": True,
        "iteration_count": 1,
        "max_iterations": 3,
    }

    payload = {"query": "FastAPI Async", "max_iterations": 3}
    headers = {"X-API-Key": settings.API_KEY}

    response = client.post("/api/v1/research", json=payload, headers=headers)

    assert response.status_code == 200
    json_data = response.json()

    assert json_data["query"] == "FastAPI Async"
    assert json_data["draft"] == "Initial draft of async FastAPI report."
    assert json_data["approved"] is True
    assert json_data["iterations_used"] == 1

    # Sources must only contain url and title (no relevant_content)
    assert len(json_data["sources"]) == 1
    source = json_data["sources"][0]
    assert source["url"] == "https://example.com/a"
    assert source["title"] == "Title A"
    assert "relevant_content" not in source

    mock_run_workflow.assert_called_once_with("FastAPI Async", 3)


@patch("app.api.v1.routes.research.run_workflow")
def test_research_route_auth_failure(mock_run_workflow):
    """Verify that calling without a valid X-API-Key returns 401 and run_workflow is never called."""
    payload = {"query": "FastAPI Async", "max_iterations": 3}

    # Case A: Missing API Key
    response = client.post("/api/v1/research", json=payload)
    assert response.status_code == 401
    assert "API Key is missing" in response.json()["message"]

    # Case B: Invalid API Key
    response = client.post(
        "/api/v1/research", json=payload, headers={"X-API-Key": "wrong-key"}
    )
    assert response.status_code == 401
    assert "Invalid API Key" in response.json()["message"]

    # Ensure run_workflow was never triggered
    assert mock_run_workflow.call_count == 0


@patch("app.api.v1.routes.research.run_workflow")
def test_research_route_validation_empty_query(mock_run_workflow):
    """Verify that an empty or whitespace-only query fails Pydantic validation with 422."""
    headers = {"X-API-Key": settings.API_KEY}

    # Case A: Empty query
    response = client.post(
        "/api/v1/research",
        json={"query": "", "max_iterations": 2},
        headers=headers,
    )
    assert response.status_code == 422

    # Case B: Whitespace-only query
    response = client.post(
        "/api/v1/research",
        json={"query": "    ", "max_iterations": 2},
        headers=headers,
    )
    assert response.status_code == 422

    # Case C: Query too short (less than 3 chars)
    response = client.post(
        "/api/v1/research",
        json={"query": "ab", "max_iterations": 2},
        headers=headers,
    )
    assert response.status_code == 422

    assert mock_run_workflow.call_count == 0


@patch("app.api.v1.routes.research.run_workflow")
def test_research_route_validation_iterations_out_of_bounds(mock_run_workflow):
    """Verify that max_iterations outside 1-5 limits fails validation with 422."""
    headers = {"X-API-Key": settings.API_KEY}

    # Case A: too low (0)
    response = client.post(
        "/api/v1/research",
        json={"query": "Valid Query", "max_iterations": 0},
        headers=headers,
    )
    assert response.status_code == 422

    # Case B: too high (6)
    response = client.post(
        "/api/v1/research",
        json={"query": "Valid Query", "max_iterations": 6},
        headers=headers,
    )
    assert response.status_code == 422

    assert mock_run_workflow.call_count == 0


@patch("app.api.v1.routes.research.run_workflow")
def test_research_route_tool_error_propagation(mock_run_workflow):
    """Verify that workflow ToolExecutionError propagates to global handler and returns 502."""
    mock_run_workflow.side_effect = ToolExecutionError("Tavily service error")

    payload = {"query": "FastAPI Async", "max_iterations": 3}
    headers = {"X-API-Key": settings.API_KEY}

    response = client.post("/api/v1/research", json=payload, headers=headers)

    # Global handler maps ToolExecutionError to status 502
    assert response.status_code == 502
    json_data = response.json()
    assert json_data["error"] == "ToolExecutionError"
    assert json_data["message"] == "Tavily service error"
    assert "request_id" in json_data


@patch("app.api.v1.routes.research.run_workflow")
def test_research_route_best_effort_approved_false(mock_run_workflow):
    """Verify that if the workflow finishes unapproved (approved=False), it returns normally with 200."""
    mock_run_workflow.return_value = {
        "query": "FastAPI Async",
        "research_sources": [],
        "reader_output": [{"url": "https://example.com/b", "title": "Title B"}],
        "draft": "Best effort draft without approval.",
        "critique_feedback": "Critique feedback rejected.",
        "approved": False,
        "iteration_count": 3,
        "max_iterations": 3,
    }

    payload = {"query": "FastAPI Async", "max_iterations": 3}
    headers = {"X-API-Key": settings.API_KEY}

    response = client.post("/api/v1/research", json=payload, headers=headers)

    assert response.status_code == 200
    json_data = response.json()
    assert json_data["approved"] is False
    assert json_data["draft"] == "Best effort draft without approval."
    assert json_data["iterations_used"] == 3
