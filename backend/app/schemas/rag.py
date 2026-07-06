from pydantic import BaseModel, Field


class RetrievedChunk(BaseModel):
    """A single passage returned by the vector search."""

    title: str | None = Field(default=None, description="Source opening name.")
    text: str = Field(description="Relevant passage of text.")
    score: float = Field(description="Cosine similarity score (higher is closer).")


class VectorSearchResponse(BaseModel):
    """Relevant passages retrieved for an opening query."""

    query: str
    results: list[RetrievedChunk] = Field(default_factory=list)
