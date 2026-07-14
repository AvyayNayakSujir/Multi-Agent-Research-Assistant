from langgraph.graph import END, StateGraph

from app.core.logging import get_logger
from app.graph.nodes import (
    critique_node,
    reader_node,
    research_node,
    writer_node,
)
from app.graph.router import route_after_critique
from app.graph.state import ResearchState

logger = get_logger(__name__)


def build_workflow() -> StateGraph:
    """Constructs and compiles the StateGraph workflow for research generation."""
    workflow = StateGraph(ResearchState)

    # Add nodes
    workflow.add_node("research_agent", research_node)
    workflow.add_node("reader_agent", reader_node)
    workflow.add_node("writer_agent", writer_node)
    workflow.add_node("critique_agent", critique_node)

    # Set entry point
    workflow.set_entry_point("research_agent")

    # Add linear edges
    workflow.add_edge("research_agent", "reader_agent")
    workflow.add_edge("reader_agent", "writer_agent")
    workflow.add_edge("writer_agent", "critique_agent")

    # Add conditional edges after critique
    workflow.add_conditional_edges(
        "critique_agent",
        route_after_critique,
        {"writer_agent": "writer_agent", "end": END},
    )

    return workflow


def run_workflow(query: str, max_iterations: int = 3) -> ResearchState:
    """Convenience function to run the compiled research workflow.

    Initializes the state and executes the graph.

    Args:
        query: The user's input research question.
        max_iterations: The maximum critique loop revisions.

    Returns:
        The final ResearchState after execution.
    """
    logger.info(
        f"Starting research workflow for query: '{query}' (max iterations: {max_iterations})"
    )

    compiled_graph = build_workflow().compile()

    initial_state = ResearchState(
        query=query,
        research_sources=[],
        reader_output=[],
        draft="",
        critique_feedback=None,
        approved=False,
        iteration_count=0,
        max_iterations=max_iterations,
    )

    final_state = compiled_graph.invoke(initial_state)

    logger.info(
        f"Workflow execution complete. Approved: {final_state.get('approved')}, "
        f"Iterations: {final_state.get('iteration_count')}/{final_state.get('max_iterations')}"
    )

    return final_state
