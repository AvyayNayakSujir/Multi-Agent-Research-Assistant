from unittest.mock import MagicMock, patch

import pytest
from tavily.errors import (
    InvalidAPIKeyError,
    MissingAPIKeyError,
    UsageLimitExceededError,
)

from app.exceptions.custom_exceptions import ToolExecutionError
from app.tools.tavily_tool import search_web


@pytest.fixture(autouse=True)
def mock_tavily_api_key(monkeypatch):
    monkeypatch.setattr("app.tools.tavily_tool.settings.TAVILY_API_KEY", "test-api-key")


@patch("app.tools.tavily_tool.TavilyClient")
def test_search_web_success(mock_tavily_client_class):
    """Verify web search succeeds on first attempt with correctly mapped results."""
    mock_client = MagicMock()
    mock_tavily_client_class.return_value = mock_client

    mock_client.search.return_value = {
        "results": [
            {
                "url": "https://example.com/result-1",
                "title": "Example Result 1",
                "content": "Example Content 1 snippet",
                "score": 0.98,
            }
        ]
    }

    results = search_web("test query", max_results=1)

    assert len(results) == 1
    assert results[0]["url"] == "https://example.com/result-1"
    assert results[0]["title"] == "Example Result 1"
    assert results[0]["content"] == "Example Content 1 snippet"
    assert results[0]["score"] == 0.98
    mock_client.search.assert_called_once_with(query="test query", max_results=1)


@patch("app.tools.tavily_tool.TavilyClient")
@patch("time.sleep", return_value=None)  # avoid delays in tests
def test_search_web_retry_success(mock_sleep, mock_tavily_client_class):
    """Verify transient error retries once and then succeeds on the second attempt."""
    mock_client = MagicMock()
    mock_tavily_client_class.return_value = mock_client

    mock_client.search.side_effect = [
        Exception("Transient network issue"),
        {
            "results": [
                {
                    "url": "https://example.com/result-2",
                    "title": "Example Result 2",
                    "content": "Example Content 2 snippet",
                    "score": 0.77,
                }
            ]
        },
    ]

    results = search_web("retry query", max_results=5)

    assert len(results) == 1
    assert results[0]["title"] == "Example Result 2"
    assert mock_client.search.call_count == 2
    mock_sleep.assert_called_once_with(1.0)


@patch("app.tools.tavily_tool.TavilyClient")
@patch("time.sleep", return_value=None)
def test_search_web_exhausted_retries_raises(mock_sleep, mock_tavily_client_class):
    """Verify general exceptions raise ToolExecutionError after retries run out."""
    mock_client = MagicMock()
    mock_tavily_client_class.return_value = mock_client
    mock_client.search.side_effect = Exception("Continuous timeout error")

    with pytest.raises(ToolExecutionError) as exc_info:
        search_web("timeout query")

    assert "Tavily API search failed after 2 attempts" in str(exc_info.value)
    assert mock_client.search.call_count == 2
    mock_sleep.assert_called_once_with(1.0)


@patch("app.tools.tavily_tool.TavilyClient")
@patch("time.sleep", return_value=None)
@pytest.mark.parametrize(
    "auth_error",
    [
        InvalidAPIKeyError("Invalid API key details"),
        MissingAPIKeyError(),
        UsageLimitExceededError("Usage limit exceeded details"),
    ],
)
def test_search_web_fail_fast_on_auth_errors(
    mock_sleep, mock_tavily_client_class, auth_error
):
    """Verify auth and limits exceptions raise ToolExecutionError immediately without retry."""
    mock_client = MagicMock()
    mock_tavily_client_class.return_value = mock_client
    mock_client.search.side_effect = auth_error

    with pytest.raises(ToolExecutionError) as exc_info:
        search_web("auth query")

    assert "Tavily API authorization or usage limit error" in str(exc_info.value)
    # Confirm it was only called once and did not sleep
    assert mock_client.search.call_count == 1
    mock_sleep.assert_not_called()
