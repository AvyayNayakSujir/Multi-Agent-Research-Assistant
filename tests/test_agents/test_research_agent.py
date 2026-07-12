from unittest.mock import MagicMock, patch

import pytest

from app.agents.research_agent import run_research_agent
from app.exceptions.custom_exceptions import ToolExecutionError
from app.models.agent_io import SearchQueries


@patch("app.agents.research_agent.TOOLS")
@patch("app.agents.research_agent.get_llm")
def test_run_research_agent_success(mock_get_llm, mock_tools):
    """Verify research agent successfully generates queries, executes search, and deduplicates by highest score."""
    # Mock LLM structured output returning two queries
    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_structured.invoke.return_value = SearchQueries(queries=["query 1", "query 2"])
    mock_structured.return_value = SearchQueries(queries=["query 1", "query 2"])
    mock_llm.with_structured_output.return_value = mock_structured
    mock_get_llm.return_value = mock_llm

    # Mock web_search function in TOOLS registry dictionary
    mock_search_web = MagicMock()
    mock_tools.__getitem__.side_effect = lambda key: (
        mock_search_web if key == "web_search" else None
    )

    # Overlapping URLs to test deduplication:
    # "https://example.com/a" is in both query results.
    # In query 1: score = 0.5
    # In query 2: score = 0.9 (should be kept)
    mock_search_web.side_effect = [
        [
            {
                "url": "https://example.com/a",
                "title": "A1",
                "content": "Content A1",
                "score": 0.5,
            },
            {
                "url": "https://example.com/b",
                "title": "B",
                "content": "Content B",
                "score": 0.8,
            },
        ],
        [
            {
                "url": "https://example.com/a",
                "title": "A2",
                "content": "Content A2",
                "score": 0.9,
            },
            {
                "url": "https://example.com/c",
                "title": "C",
                "content": "Content C",
                "score": 0.6,
            },
        ],
    ]

    results = run_research_agent("What is FastAPI?", max_results_per_query=5)

    # 3 distinct URLs (a, b, c) after deduplication
    assert len(results) == 3

    # Verify deduplication kept the highest scoring version of A
    a_result = next(r for r in results if r["url"] == "https://example.com/a")
    assert a_result["score"] == 0.9
    assert a_result["title"] == "A2"

    # Verify other results exist
    assert any(r["url"] == "https://example.com/b" for r in results)
    assert any(r["url"] == "https://example.com/c" for r in results)

    # Confirm search was executed for both queries
    assert mock_search_web.call_count == 2
    mock_search_web.assert_any_call("query 1", max_results=5)
    mock_search_web.assert_any_call("query 2", max_results=5)


@patch("app.agents.research_agent.TOOLS")
@patch("app.agents.research_agent.get_llm")
def test_run_research_agent_partial_failure(mock_get_llm, mock_tools):
    """Verify research agent handles partial Tavily failure and continues with other query results."""
    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_structured.invoke.return_value = SearchQueries(queries=["query 1", "query 2"])
    mock_structured.return_value = SearchQueries(queries=["query 1", "query 2"])
    mock_llm.with_structured_output.return_value = mock_structured
    mock_get_llm.return_value = mock_llm

    mock_search_web = MagicMock()
    mock_tools.__getitem__.side_effect = lambda key: (
        mock_search_web if key == "web_search" else None
    )

    # First search succeeds, second raises ToolExecutionError
    mock_search_web.side_effect = [
        [
            {
                "url": "https://example.com/success",
                "title": "Success",
                "content": "Content",
                "score": 0.9,
            }
        ],
        ToolExecutionError("Tavily service limit reached"),
    ]

    results = run_research_agent("Python async", max_results_per_query=3)

    # Agent still completes and returns results from first query
    assert len(results) == 1
    assert results[0]["url"] == "https://example.com/success"
    assert mock_search_web.call_count == 2


@patch("app.agents.research_agent.TOOLS")
@patch("app.agents.research_agent.get_llm")
def test_run_research_agent_total_failure(mock_get_llm, mock_tools):
    """Verify research agent raises ToolExecutionError if all Tavily queries fail."""
    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_structured.invoke.return_value = SearchQueries(queries=["query 1", "query 2"])
    mock_structured.return_value = SearchQueries(queries=["query 1", "query 2"])
    mock_llm.with_structured_output.return_value = mock_structured
    mock_get_llm.return_value = mock_llm

    mock_search_web = MagicMock()
    mock_tools.__getitem__.side_effect = lambda key: (
        mock_search_web if key == "web_search" else None
    )

    # Both search queries fail
    mock_search_web.side_effect = [
        ToolExecutionError("Network Timeout"),
        ToolExecutionError("Unauthorized key"),
    ]

    with pytest.raises(ToolExecutionError) as exc_info:
        run_research_agent("GraphQL query", max_results_per_query=5)

    assert "All generated search queries failed to execute" in str(exc_info.value)
    assert mock_search_web.call_count == 2
