from pydantic import BaseModel, Field, field_validator


class ResearchRequest(BaseModel):
    """API Request model for starting a research workflow execution."""

    query: str = Field(
        ...,
        description="The research query / topic to explore.",
    )
    max_iterations: int = Field(
        default=3,
        description="Maximum number of critique-to-writer feedback iterations (1 to 5).",
    )

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        stripped = v.strip()
        if len(stripped) < 3 or len(stripped) > 500:
            raise ValueError(
                "Query must be between 3 and 500 characters after stripping whitespace."
            )
        return stripped

    @field_validator("max_iterations")
    @classmethod
    def validate_max_iterations(cls, v: int) -> int:
        if v < 1 or v > 5:
            raise ValueError(
                "max_iterations must be an integer between 1 and 5 inclusive."
            )
        return v


class SourceInfo(BaseModel):
    """Information representing a source page used during synthesis."""

    url: str
    title: str


class ResearchResponse(BaseModel):
    """API Response model containing the research execution results."""

    query: str
    draft: str
    approved: bool
    iterations_used: int
    sources: list[SourceInfo]
