"""Schémas Pydantic des réponses de la recherche vectorielle (RAG).

Ces modèles définissent la structure des passages Wikichess renvoyés par la route
``/vector-search`` après la recherche dans Milvus.
"""

from pydantic import BaseModel, Field


class RetrievedChunk(BaseModel):
    """Un passage de texte renvoyé par la recherche vectorielle."""

    title: str | None = Field(default=None, description="Nom de l'ouverture source.")
    text: str = Field(description="Passage de texte pertinent.")
    score: float = Field(
        description="Score de similarité cosinus (plus haut = plus proche)."
    )


class VectorSearchResponse(BaseModel):
    """Passages pertinents récupérés pour une requête d'ouverture."""

    query: str
    results: list[RetrievedChunk] = Field(default_factory=list)
