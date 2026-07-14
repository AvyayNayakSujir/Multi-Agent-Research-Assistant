from app.core.logging import get_logger
from app.graph.state import ResearchState

logger = get_logger(__name__)


def route_after_critique(state: ResearchState) -> str:
    """Conditional router determining the next step after draft critique.

    Returns "end" if the draft is approved or if iteration count exceeds the maximum limit,
    otherwise returns "writer_agent" for a revision cycle.

    Args:
        state: The current ResearchState.

    Returns:
        "end" or "writer_agent".
    """
    iteration = state.get("iteration_count", 0)
    max_iter = state.get("max_iterations", 3)
    approved = state.get("approved", False)

    if approved:
        logger.info(
            f"Draft has been approved by critique. Exiting workflow at iteration {iteration}."
        )
        return "end"

    if iteration >= max_iter:
        logger.info(
            f"Max critique iterations ({max_iter}) reached without approval. "
            f"Exiting workflow with a best-effort draft."
        )
        return "end"

    logger.info(
        f"Draft rejected by critique. Heading to revision pass. "
        f"Iteration count: {iteration}/{max_iter}."
    )
    return "writer_agent"
