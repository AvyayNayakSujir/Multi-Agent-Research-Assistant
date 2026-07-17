from typing import AsyncGenerator
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


async def run_workflow_stream(
    query: str, max_iterations: int = 3
) -> AsyncGenerator[dict, None]:
    """Runs the compiled research workflow, yielding status updates in real-time.

    Args:
        query: The user's input research question.
        max_iterations: The maximum critique loop revisions.

    Yields:
        Dictionaries containing either 'status' or 'result' updates.
    """
    logger.info(
        f"Starting streaming research workflow for query: '{query}' (max iterations: {max_iterations})"
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

    # Yield initial search status
    yield {"type": "status", "message": "Searching sources..."}

    current_state = initial_state.copy()
    async for chunk in compiled_graph.astream(initial_state):
        # Update current_state with the chunk changes so we have the full state at the end
        for node_name, updates in chunk.items():
            current_state.update(updates)

            if node_name == "research_agent":
                yield {"type": "status", "message": "Scraping & filtering content..."}
            elif node_name == "reader_agent":
                yield {"type": "status", "message": "Retrieving info..."}
            elif node_name == "writer_agent":
                yield {"type": "status", "message": "Drafting report..."}
            elif node_name == "critique_agent":
                approved = updates.get("approved", False)
                iteration = current_state.get("iteration_count", 0)
                if not approved and iteration < max_iterations:
                    yield {
                        "type": "status",
                        "message": f"Revising the report...",
                    }
                else:
                    yield {"type": "status", "message": "Finalizing report..."}

    # At the end, yield the final complete state
    yield {"type": "result", "state": current_state}
