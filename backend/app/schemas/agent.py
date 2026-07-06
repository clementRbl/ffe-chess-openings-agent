"""Schémas Pydantic de la réponse de l'agent d'analyse.

Ces modèles décrivent la recommandation complète renvoyée par la route
``/analyze/{fen}`` : coups théoriques, évaluation moteur, contexte, vidéos, un
résumé lisible et l'état de chaque source (pour une dégradation gracieuse).
"""

from pydantic import BaseModel, Field

from app.schemas.chess import EvaluationResponse, TheoreticalMove
from app.schemas.rag import RetrievedChunk
from app.schemas.video import VideoResult


class SourceStatus(BaseModel):
    """État d'une source d'information consultée par l'agent."""

    ok: bool = Field(default=True, description="Vrai si la source a répondu.")
    detail: str | None = Field(
        default=None, description="Message d'erreur si la source a échoué."
    )


class AgentAnalysis(BaseModel):
    """Recommandation complète de l'agent pour une position donnée."""

    fen: str
    opening: str | None = Field(
        default=None, description="Nom de l'ouverture si la position est reconnue."
    )
    in_theory: bool = Field(
        default=False, description="Vrai si des coups théoriques ont été trouvés."
    )
    theoretical_moves: list[TheoreticalMove] = Field(default_factory=list)
    evaluation: EvaluationResponse | None = None
    context: list[RetrievedChunk] = Field(default_factory=list)
    videos: list[VideoResult] = Field(default_factory=list)
    summary: str = Field(default="", description="Résumé lisible de la recommandation.")
    sources: dict[str, SourceStatus] = Field(
        default_factory=dict, description="État de chaque source consultée."
    )
