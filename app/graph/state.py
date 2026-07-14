from typing import TypedDict


class ResearchState(TypedDict):
    """The state of the multi-agent research workflow."""

    query: str
    research_sources: list[dict]
    reader_output: list[dict]
    draft: str
    critique_feedback: str | None
    approved: bool
    iteration_count: int
    max_iterations: int
