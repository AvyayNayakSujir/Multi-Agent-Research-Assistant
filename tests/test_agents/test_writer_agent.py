from unittest.mock import MagicMock, patch

import pytest

from app.agents.writer_agent import run_writer_agent
from app.exceptions.custom_exceptions import AgentTimeoutError


@patch("app.agents.writer_agent.get_llm")
def test_run_writer_agent_first_draft(mock_get_llm):
    """Verify first-draft mode correctly generates a report from scratch and returns a string."""
    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = "Initial synthesized draft content."
    mock_llm.invoke.return_value = mock_response
    mock_llm.return_value = mock_response
    mock_get_llm.return_value = mock_llm

    sources = [
        {
            "url": "https://source1.com",
            "title": "Source 1",
            "relevant_content": "Content 1",
        }
    ]

    draft = run_writer_agent("FastAPI Overview", sources)

    assert draft == "Initial synthesized draft content."
    assert mock_llm.call_count == 1
    # Check that it uses WRITER_PROMPT (which contains 'user: Research Query: ...')
    args, kwargs = mock_llm.call_args
    prompt_str = str(args[0])
    assert "FastAPI Overview" in prompt_str
    assert "Source 1" in prompt_str


@patch("app.agents.writer_agent.get_llm")
def test_run_writer_agent_revision(mock_get_llm):
    """Verify revision mode correctly refines previous draft based on critique feedback."""
    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = "Revised draft content addressing feedback."
    mock_llm.invoke.return_value = mock_response
    mock_llm.return_value = mock_response
    mock_get_llm.return_value = mock_llm

    sources = [
        {
            "url": "https://source1.com",
            "title": "Source 1",
            "relevant_content": "Content 1",
        }
    ]

    draft = run_writer_agent(
        query="Async python",
        sources=sources,
        critique_feedback="Missing async event loop details.",
        previous_draft="Draft v1 about async.",
    )

    assert draft == "Revised draft content addressing feedback."
    assert mock_llm.call_count == 1

    # Check that feedback and previous draft are in what is sent to the LLM
    args, kwargs = mock_llm.call_args
    prompt_str = str(args[0])
    assert "Missing async event loop details." in prompt_str
    assert "Draft v1 about async." in prompt_str
    assert "Content 1" in prompt_str


def test_run_writer_agent_empty_sources():
    """Verify empty sources list raises ValueError immediately before any LLM call."""
    with patch("app.agents.writer_agent.get_llm") as mock_get_llm:
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm

        with pytest.raises(ValueError) as exc_info:
            run_writer_agent("Query", [])

        assert "Sources list cannot be empty" in str(exc_info.value)
        assert mock_llm.call_count == 0


@patch("app.agents.writer_agent.get_llm")
def test_run_writer_agent_inconsistent_mode_args(mock_get_llm):
    """Verify that passing exactly one of critique_feedback or previous_draft raises ValueError."""
    mock_llm = MagicMock()
    mock_get_llm.return_value = mock_llm

    sources = [{"url": "https://example.com"}]

    # Case A: only feedback provided
    with pytest.raises(ValueError) as exc_info:
        run_writer_agent("Query", sources, critique_feedback="Feedback only")
    assert "Both critique_feedback and previous_draft must be provided" in str(
        exc_info.value
    )

    # Case B: only draft provided
    with pytest.raises(ValueError) as exc_info:
        run_writer_agent("Query", sources, previous_draft="Draft only")
    assert "Both critique_feedback and previous_draft must be provided" in str(
        exc_info.value
    )

    assert mock_llm.call_count == 0


@patch("app.agents.writer_agent.get_llm")
def test_run_writer_agent_timeout_propagation(mock_get_llm):
    """Verify that AgentTimeoutError from timed out LLM call propagates uncaught."""
    mock_llm = MagicMock()
    # Mock chain.invoke or llm.invoke to raise AgentTimeoutError
    mock_llm.side_effect = AgentTimeoutError("LLM call timed out")
    mock_llm.invoke.side_effect = AgentTimeoutError("LLM call timed out")
    mock_get_llm.return_value = mock_llm

    sources = [{"url": "https://example.com"}]

    with pytest.raises(AgentTimeoutError) as exc_info:
        run_writer_agent("Query", sources)

    assert "LLM call timed out" in str(exc_info.value)
