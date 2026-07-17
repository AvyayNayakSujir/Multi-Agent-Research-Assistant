import asyncio
import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import verify_api_key
from app.graph.workflow import run_workflow, run_workflow_stream
from app.middleware.rate_limit import limiter
from app.models.schemas import ResearchRequest, ResearchResponse, SourceInfo

logger = get_logger(__name__)

router = APIRouter()


@router.post(
    "/research",
    response_model=ResearchResponse,
    dependencies=[Depends(verify_api_key)],
)
@limiter.limit(settings.RATE_LIMIT)
async def start_research(
    request: Request, payload: ResearchRequest
) -> ResearchResponse:
    """Execute the multi-agent research workflow.

    Runs the LangGraph research-reader-writer-critique loop in a separate thread
    to prevent blocking the FastAPI event loop.
    """
    query = payload.query
    max_iter = payload.max_iterations

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


@router.post(
    "/research/stream",
    dependencies=[Depends(verify_api_key)],
)
@limiter.limit(settings.RATE_LIMIT)
async def start_research_stream(
    request: Request, payload: ResearchRequest
) -> StreamingResponse:
    """Execute the multi-agent research workflow, streaming status updates in real-time.

    Returns a Server-Sent Events (SSE) stream of status updates, concluding with the
    final research report response.
    """
    query = payload.query
    max_iter = payload.max_iterations

    truncated_query = query[:100] + "..." if len(query) > 100 else query
    logger.info(
        f"API request '/research/stream' received: query='{truncated_query}', max_iterations={max_iter}"
    )

    async def event_generator():
        try:
            async for update in run_workflow_stream(query, max_iter):
                if update["type"] == "status":
                    yield f"data: {json.dumps({'type': 'status', 'message': update['message']})}\n\n"
                elif update["type"] == "result":
                    final_state = update["state"]
                    reader_output = final_state.get("reader_output", [])
                    sources_mapped = [
                        {
                            "url": src.get("url", "No URL"),
                            "title": src.get("title") or "Untitled Source",
                        }
                        for src in reader_output
                    ]

                    # Convert to response dictionary format matching ResearchResponse schema
                    result_payload = {
                        "query": final_state.get("query", query),
                        "draft": final_state.get("draft", ""),
                        "approved": final_state.get("approved", False),
                        "iterations_used": final_state.get("iteration_count", 0),
                        "sources": sources_mapped,
                    }
                    yield f"data: {json.dumps({'type': 'result', 'payload': result_payload})}\n\n"
        except Exception as exc:
            logger.error(f"Error during streaming research: {exc}", exc_info=True)
            error_payload = {
                "type": "error",
                "error": type(exc).__name__,
                "message": str(exc),
            }
            yield f"data: {json.dumps(error_payload)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
