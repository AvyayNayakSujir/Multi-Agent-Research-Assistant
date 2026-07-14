from app.agents.critique_agent import run_critique_agent
from app.agents.reader_agent import run_reader_agent
from app.agents.research_agent import run_research_agent
from app.agents.writer_agent import run_writer_agent
from app.core.logging import get_logger
from app.graph.state import ResearchState

logger = get_logger(__name__)


def research_node(state: ResearchState) -> dict:
    """Executes the research agent to generate search queries and fetch sources."""
    query = state["query"]
    logger.info(f"Node 'research_agent': starting search for query: '{query}'")
    sources = run_research_agent(query)
    return {"research_sources": sources}


def reader_node(state: ResearchState) -> dict:
    """Executes the reader agent to scrape and condense raw search sources."""
    query = state["query"]
    sources = state.get("research_sources", [])
    logger.info(f"Node 'reader_agent': scraping and condensing {len(sources)} sources.")
    reader_output = run_reader_agent(query, sources)
    return {"reader_output": reader_output}


def writer_node(state: ResearchState) -> dict:
    """Executes the writer agent to write a first draft or revise a previous draft."""
    query = state["query"]
    sources = state.get("reader_output", [])
    feedback = state.get("critique_feedback")
    prev_draft = state.get("draft")

    # Strict truthiness check instead of key-existence to safely distinguish modes
    if feedback and prev_draft:
        logger.info("Node 'writer_agent': executing revision mode.")
        draft = run_writer_agent(
            query=query,
            sources=sources,
            critique_feedback=feedback,
            previous_draft=prev_draft,
        )
    else:
        logger.info(
            "Node 'writer_agent': executing first-draft mode (no previous feedback)."
        )
        draft = run_writer_agent(
            query=query,
            sources=sources,
            critique_feedback=None,
            previous_draft=None,
        )

    return {"draft": draft}


def critique_node(state: ResearchState) -> dict:
    """Executes the critique agent to evaluate the current draft."""
    query = state["query"]
    draft = state.get("draft", "")
    sources = state.get("reader_output", [])
    iteration = state.get("iteration_count", 0)

    logger.info(
        f"Node 'critique_agent': starting critique pass (current iteration: {iteration})."
    )
    result = run_critique_agent(query=query, draft=draft, sources=sources)

    return {
        "approved": result.approved,
        "critique_feedback": result.feedback,
        "iteration_count": iteration + 1,
    }
