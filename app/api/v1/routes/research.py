import asyncio

from fastapi import APIRouter, Depends

from app.core.logging import get_logger
from app.core.security import verify_api_key
from app.graph.workflow import run_workflow
from app.models.schemas import ResearchRequest, ResearchResponse, SourceInfo

logger = get_logger(__name__)

router = APIRouter()


@router.post(
    "/research",
    response_model=ResearchResponse,
    dependencies=[Depends(verify_api_key)],
)
async def start_research(request: ResearchRequest) -> ResearchResponse:
    """Execute the multi-agent research workflow.

    Runs the LangGraph research-reader-writer-critique loop in a separate thread
    to prevent blocking the FastAPI event loop.
    """
    query = request.query
    max_iter = request.max_iterations

    # Log incoming request (truncate query if very long)
    truncated_query = query[:100] + "..." if len(query) > 100 else query
    logger.info(
        f"API request '/research' received: query='{truncated_query}', max_iterations={max_iter}"
    )

    # run_workflow is a blocking synchronous function.
    # calling it directly would block the single-threaded asyncio event loop.
    # to avoid this, we offload the call to a separate worker thread.
    final_state = await asyncio.to_thread(run_workflow, query, max_iter)

    approved = final_state.get("approved", False)
    iterations_used = final_state.get("iteration_count", 0)

    # Log completion details
    logger.info(
        f"API request '/research' complete. approved={approved}, iterations_used={iterations_used}"
    )

    # Map state to ResearchResponse.
    # sources are mapped from final_state["reader_output"], keeping only url and title.
    reader_output = final_state.get("reader_output", [])
    sources_mapped = [
        SourceInfo(
            url=src.get("url", "No URL"),
            title=src.get("title") or "Untitled Source",
        )
        for src in reader_output
    ]

    return ResearchResponse(
        query=final_state.get("query", query),
        draft=final_state.get("draft", ""),
        approved=approved,
        iterations_used=iterations_used,
        sources=sources_mapped,
    )
