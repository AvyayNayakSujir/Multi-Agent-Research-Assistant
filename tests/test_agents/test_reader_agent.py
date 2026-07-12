from unittest.mock import MagicMock, patch

import pytest

from app.agents.reader_agent import run_reader_agent
from app.exceptions.custom_exceptions import ToolExecutionError
from app.models.agent_io import CondensedContent


@patch("app.agents.reader_agent.TOOLS")
@patch("app.agents.reader_agent.get_llm")
def test_run_reader_agent_success(mock_get_llm, mock_tools):
    """Verify success path: multiple sources scraped, condensed, and formatted correctly."""
    # Mock LLM
    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_structured.invoke.return_value = CondensedContent(
        is_relevant=True, relevant_content="Extracted facts and statistics."
    )
    mock_structured.return_value = CondensedContent(
        is_relevant=True, relevant_content="Extracted facts and statistics."
    )
    mock_llm.with_structured_output.return_value = mock_structured
    mock_get_llm.return_value = mock_llm

    # Mock scrape_url registry function
    mock_scrape_url = MagicMock()
    mock_tools.__getitem__.side_effect = lambda key: (
        mock_scrape_url if key == "scrape_url" else None
    )

    mock_scrape_url.return_value = {
        "url": "https://example.com/a",
        "title": "Title A",
        "text": "Cleaned full page text.",
        "success": True,
    }

    sources = [
        {"url": "https://example.com/a", "title": "Title A", "score": 0.95},
        {"url": "https://example.com/b", "title": "Title B", "score": 0.85},
    ]

    results = run_reader_agent("My Query", sources, max_sources=5)

    assert len(results) == 2
    assert results[0]["url"] == "https://example.com/a"
    assert results[0]["title"] == "Title A"
    assert results[0]["relevant_content"] == "Extracted facts and statistics."
    assert mock_scrape_url.call_count == 2


@patch("app.agents.reader_agent.TOOLS")
@patch("app.agents.reader_agent.get_llm")
def test_run_reader_agent_partial_scrape_failure(mock_get_llm, mock_tools):
    """Verify that scrape failures are skipped and results of successful scrapes are returned."""
    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_structured.return_value = CondensedContent(
        is_relevant=True, relevant_content="Some relevant facts."
    )
    mock_llm.with_structured_output.return_value = mock_structured
    mock_get_llm.return_value = mock_llm

    mock_scrape_url = MagicMock()
    mock_tools.__getitem__.side_effect = lambda key: (
        mock_scrape_url if key == "scrape_url" else None
    )

    # First succeeds, second fails
    mock_scrape_url.side_effect = [
        {
            "url": "https://success.com",
            "title": "Success",
            "text": "Success text",
            "success": True,
        },
        {"url": "https://fail.com", "title": None, "text": "", "success": False},
    ]

    sources = [
        {"url": "https://success.com", "title": "Success", "score": 0.9},
        {"url": "https://fail.com", "title": "Fail", "score": 0.8},
    ]

    results = run_reader_agent("Query", sources)

    assert len(results) == 1
    assert results[0]["url"] == "https://success.com"
    assert results[0]["relevant_content"] == "Some relevant facts."
    assert mock_scrape_url.call_count == 2


@patch("app.agents.reader_agent.TOOLS")
@patch("app.agents.reader_agent.get_llm")
def test_run_reader_agent_total_scrape_failure(mock_get_llm, mock_tools):
    """Verify that if all sources fail to scrape, ToolExecutionError is raised."""
    mock_scrape_url = MagicMock()
    mock_tools.__getitem__.side_effect = lambda key: (
        mock_scrape_url if key == "scrape_url" else None
    )
    mock_scrape_url.return_value = {"success": False}

    sources = [
        {"url": "https://fail1.com", "score": 0.9},
        {"url": "https://fail2.com", "score": 0.8},
    ]

    with pytest.raises(ToolExecutionError) as exc_info:
        run_reader_agent("Query", sources)

    assert "All sources failed to scrape or yield relevant content." in str(
        exc_info.value
    )
    assert mock_scrape_url.call_count == 2


@patch("app.agents.reader_agent.TOOLS")
@patch("app.agents.reader_agent.get_llm")
def test_run_reader_agent_condensation_fallback(mock_get_llm, mock_tools):
    """Verify that if LLM condensation fails, the raw text truncated to 2000 chars is used."""
    mock_llm = MagicMock()
    mock_structured = MagicMock()
    # LLM invoke raises Exception
    mock_structured.side_effect = Exception("LLM connection timed out")
    mock_structured.return_value = Exception("LLM connection timed out")
    mock_llm.with_structured_output.return_value = mock_structured
    mock_get_llm.return_value = mock_llm

    mock_scrape_url = MagicMock()
    mock_tools.__getitem__.side_effect = lambda key: (
        mock_scrape_url if key == "scrape_url" else None
    )

    # Scrape returns very long text
    long_raw_text = "rawcontent" * 300  # 3000 chars
    mock_scrape_url.return_value = {
        "url": "https://example.com/fallback",
        "title": "Fallback",
        "text": long_raw_text,
        "success": True,
    }

    sources = [{"url": "https://example.com/fallback", "score": 0.9}]

    results = run_reader_agent("Query", sources)

    assert len(results) == 1
    assert results[0]["url"] == "https://example.com/fallback"
    # Content must be truncated to exactly 2000 characters
    assert len(results[0]["relevant_content"]) == 2000
    assert results[0]["relevant_content"] == long_raw_text[:2000]


@patch("app.agents.reader_agent.TOOLS")
@patch("app.agents.reader_agent.get_llm")
def test_run_reader_agent_max_sources_capping(mock_get_llm, mock_tools):
    """Verify that max_sources successfully limits the sources processed."""
    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_structured.return_value = CondensedContent(
        is_relevant=True, relevant_content="content"
    )
    mock_llm.with_structured_output.return_value = mock_structured
    mock_get_llm.return_value = mock_llm

    mock_scrape_url = MagicMock()
    mock_tools.__getitem__.side_effect = lambda key: (
        mock_scrape_url if key == "scrape_url" else None
    )
    mock_scrape_url.return_value = {"success": True, "text": "content"}

    sources = [
        {"url": "https://example.com/1", "score": 0.95},
        {"url": "https://example.com/2", "score": 0.90},
        {"url": "https://example.com/3", "score": 0.85},
    ]

    results = run_reader_agent("Query", sources, max_sources=2)

    # Should only process top 2 sources (score 0.95 and 0.90)
    assert len(results) == 2
    assert mock_scrape_url.call_count == 2
    mock_scrape_url.assert_any_call("https://example.com/1")
    mock_scrape_url.assert_any_call("https://example.com/2")
    # Verify the lowest score was not processed
    with pytest.raises(AssertionError):
        mock_scrape_url.assert_any_call("https://example.com/3")


@patch("app.agents.reader_agent.TOOLS")
@patch("app.agents.reader_agent.get_llm")
def test_run_reader_agent_irrelevance_filtering(mock_get_llm, mock_tools):
    """Verify that pages returning is_relevant: False are excluded from final output."""
    mock_llm = MagicMock()
    mock_structured = MagicMock()
    # First is relevant, second is irrelevant
    mock_structured.side_effect = [
        CondensedContent(is_relevant=True, relevant_content="Important info."),
        CondensedContent(is_relevant=False, relevant_content=""),
    ]
    mock_llm.with_structured_output.return_value = mock_structured
    mock_get_llm.return_value = mock_llm

    mock_scrape_url = MagicMock()
    mock_tools.__getitem__.side_effect = lambda key: (
        mock_scrape_url if key == "scrape_url" else None
    )
    mock_scrape_url.return_value = {"success": True, "text": "content"}

    sources = [
        {"url": "https://example.com/relevant", "score": 0.95},
        {"url": "https://example.com/junk", "score": 0.90},
    ]

    results = run_reader_agent("Query", sources)

    assert len(results) == 1
    assert results[0]["url"] == "https://example.com/relevant"
    assert results[0]["relevant_content"] == "Important info."


@patch("app.agents.reader_agent.TOOLS")
@patch("app.agents.reader_agent.get_llm")
def test_run_reader_agent_total_irrelevance_raises(mock_get_llm, mock_tools):
    """Verify that if all sources are marked irrelevant, ToolExecutionError is raised."""
    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_structured.return_value = CondensedContent(
        is_relevant=False, relevant_content=""
    )
    mock_llm.with_structured_output.return_value = mock_structured
    mock_get_llm.return_value = mock_llm

    mock_scrape_url = MagicMock()
    mock_tools.__getitem__.side_effect = lambda key: (
        mock_scrape_url if key == "scrape_url" else None
    )
    mock_scrape_url.return_value = {"success": True, "text": "content"}

    sources = [
        {"url": "https://example.com/junk1", "score": 0.95},
        {"url": "https://example.com/junk2", "score": 0.90},
    ]

    with pytest.raises(ToolExecutionError) as exc_info:
        run_reader_agent("Query", sources)

    assert "All sources failed to scrape or yield relevant content." in str(
        exc_info.value
    )
    assert mock_scrape_url.call_count == 2
