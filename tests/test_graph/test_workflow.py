from unittest.mock import patch

import pytest

from app.exceptions.custom_exceptions import ToolExecutionError
from app.graph.workflow import run_workflow
from app.models.agent_io import CritiqueOutput


@patch("app.graph.nodes.run_critique_agent")
@patch("app.graph.nodes.run_writer_agent")
@patch("app.graph.nodes.run_reader_agent")
@patch("app.graph.nodes.run_research_agent")
def test_run_workflow_happy_path_immediate_approval(
    mock_run_research, mock_run_reader, mock_run_writer, mock_run_critique
):
    """Verify happy path: approved on first pass. No revision loops."""
    # Set up mock returns
    mock_run_research.return_value = [{"url": "https://a.com", "score": 0.9}]
    mock_run_reader.return_value = [
        {"url": "https://a.com", "relevant_content": "Facts"}
    ]
    mock_run_writer.return_value = "Draft content"
    mock_run_critique.return_value = CritiqueOutput(
        approved=True, feedback="Looks good."
    )

    final_state = run_workflow("Query text", max_iterations=3)

    # Assertions
    assert final_state["approved"] is True
    assert final_state["draft"] == "Draft content"
    assert final_state["iteration_count"] == 1
    assert final_state["critique_feedback"] == "Looks good."

    # Verify call counts: each agent should be called exactly once
    mock_run_research.assert_called_once_with("Query text")
    mock_run_reader.assert_called_once_with(
        "Query text", [{"url": "https://a.com", "score": 0.9}]
    )
    mock_run_writer.assert_called_once_with(
        query="Query text",
        sources=[{"url": "https://a.com", "relevant_content": "Facts"}],
        critique_feedback=None,
        previous_draft=None,
    )
    mock_run_critique.assert_called_once_with(
        query="Query text",
        draft="Draft content",
        sources=[{"url": "https://a.com", "relevant_content": "Facts"}],
    )


@patch("app.graph.nodes.run_critique_agent")
@patch("app.graph.nodes.run_writer_agent")
@patch("app.graph.nodes.run_reader_agent")
@patch("app.graph.nodes.run_research_agent")
def test_run_workflow_revision_loop_and_approval(
    mock_run_research, mock_run_reader, mock_run_writer, mock_run_critique
):
    """Verify loop then approved path: critique rejects once, then approves on second try.

    Asserts that the second writer call receives the exact strings produced by the first pass.
    """
    mock_run_research.return_value = [{"url": "https://a.com"}]
    mock_run_reader.return_value = [
        {"url": "https://a.com", "relevant_content": "Facts"}
    ]

    # Writer returns initial draft first, then revised draft
    mock_run_writer.side_effect = ["Initial Draft", "Revised Draft"]

    # Critique rejects first time with specific feedback, approves second time
    mock_run_critique.side_effect = [
        CritiqueOutput(approved=False, feedback="Fix X."),
        CritiqueOutput(approved=True, feedback="Approved!"),
    ]

    final_state = run_workflow("Query text", max_iterations=3)

    # State checks
    assert final_state["approved"] is True
    assert final_state["draft"] == "Revised Draft"
    assert final_state["iteration_count"] == 2
    assert final_state["critique_feedback"] == "Approved!"

    # Call assertions
    assert mock_run_research.call_count == 1
    assert mock_run_reader.call_count == 1

    # Writer agent called twice:
    # 1st time with None inputs
    # 2nd time with exact previous draft and critique feedback strings
    assert mock_run_writer.call_count == 2
    mock_run_writer.assert_any_call(
        query="Query text",
        sources=[{"url": "https://a.com", "relevant_content": "Facts"}],
        critique_feedback=None,
        previous_draft=None,
    )
    mock_run_writer.assert_any_call(
        query="Query text",
        sources=[{"url": "https://a.com", "relevant_content": "Facts"}],
        critique_feedback="Fix X.",
        previous_draft="Initial Draft",
    )

    assert mock_run_critique.call_count == 2
    mock_run_critique.assert_any_call(
        query="Query text",
        draft="Initial Draft",
        sources=[{"url": "https://a.com", "relevant_content": "Facts"}],
    )
    mock_run_critique.assert_any_call(
        query="Query text",
        draft="Revised Draft",
        sources=[{"url": "https://a.com", "relevant_content": "Facts"}],
    )


@patch("app.graph.nodes.run_critique_agent")
@patch("app.graph.nodes.run_writer_agent")
@patch("app.graph.nodes.run_reader_agent")
@patch("app.graph.nodes.run_research_agent")
def test_run_workflow_max_iterations_exhausted(
    mock_run_research, mock_run_reader, mock_run_writer, mock_run_critique
):
    """Verify max iterations exhausted: critique always rejects. Stops at max, no exception."""
    mock_run_research.return_value = [{"url": "https://a.com"}]
    mock_run_reader.return_value = [
        {"url": "https://a.com", "relevant_content": "Facts"}
    ]

    # Writer returns distinct drafts
    mock_run_writer.side_effect = ["Draft 1", "Draft 2", "Draft 3"]

    # Critique always rejects
    mock_run_critique.return_value = CritiqueOutput(
        approved=False, feedback="Never good enough."
    )

    # Run with max_iterations = 2
    final_state = run_workflow("Query text", max_iterations=2)

    # State checks: iteration_count is 2, approved is False, draft is Draft 2 (best-effort)
    assert final_state["approved"] is False
    assert final_state["iteration_count"] == 2
    assert final_state["draft"] == "Draft 2"
    assert final_state["critique_feedback"] == "Never good enough."

    # Ensure no infinite loop: writer/critique called exactly 2 times (the max iterations)
    assert mock_run_writer.call_count == 2
    assert mock_run_critique.call_count == 2


@patch("app.graph.nodes.run_research_agent")
def test_run_workflow_upstream_failure_propagation(mock_run_research):
    """Verify that an exception raised by an agent node propagates out of workflow uncaught."""
    # Research agent fails completely
    mock_run_research.side_effect = ToolExecutionError("Tavily rate limits exceeded.")

    with pytest.raises(ToolExecutionError) as exc_info:
        run_workflow("Query text")

    assert "Tavily rate limits exceeded" in str(exc_info.value)
