"""Schémas Pydantic des réponses liées aux échecs.

Ces modèles définissent la structure (et la validation) des réponses JSON
renvoyées par les routes ``/moves`` et ``/evaluate`` : coups théoriques issus de
Lichess et évaluation de Stockfish.
"""

from pydantic import BaseModel, Field


class TheoreticalMove(BaseModel):
    """Un coup proposé par l'explorateur d'ouvertures Lichess."""

    uci: str = Field(description="Coup en notation UCI, ex. 'e2e4'.")
    san: str = Field(description="Coup en notation SAN, ex. 'e4'.")
    white: int = Field(
        description="Nombre de parties de référence gagnées par les Blancs."
    )
    draws: int = Field(description="Nombre de parties de référence nulles.")
    black: int = Field(
        description="Nombre de parties de référence gagnées par les Noirs."
    )
    total: int = Field(description="Nombre total de parties de référence avec ce coup.")


class MovesResponse(BaseModel):
    """Coups théoriques disponibles depuis une position donnée."""

    fen: str
    opening: str | None = Field(
        default=None, description="Nom de l'ouverture si la position est reconnue."
    )
    moves: list[TheoreticalMove] = Field(default_factory=list)


class EvaluationResponse(BaseModel):
    """Évaluation d'une position par le moteur Stockfish."""

    fen: str
    type: str = Field(description="Type d'évaluation : 'cp' (centipions) ou 'mate'.")
    value: int = Field(
        description="Centipions du point de vue du trait, ou nombre de coups "
        "avant le mat lorsque le type vaut 'mate'."
    )
    best_move: str | None = Field(
        default=None, description="Meilleur coup selon Stockfish, en notation UCI."
    )
