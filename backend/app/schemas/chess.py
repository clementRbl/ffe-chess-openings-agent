from pydantic import BaseModel, Field


class TheoreticalMove(BaseModel):
    """A single move suggested by the Lichess opening explorer."""

    uci: str = Field(description="Move in UCI notation, e.g. 'e2e4'.")
    san: str = Field(description="Move in SAN notation, e.g. 'e4'.")
    white: int = Field(description="Number of reference games won by White.")
    draws: int = Field(description="Number of reference games drawn.")
    black: int = Field(description="Number of reference games won by Black.")
    total: int = Field(description="Total number of reference games with this move.")


class MovesResponse(BaseModel):
    """Theoretical moves available from a given position."""

    fen: str
    opening: str | None = Field(
        default=None, description="Opening name if the position is recognised."
    )
    moves: list[TheoreticalMove] = Field(default_factory=list)


class EvaluationResponse(BaseModel):
    """Stockfish evaluation of a given position."""

    fen: str
    type: str = Field(description="Evaluation type: 'cp' (centipawns) or 'mate'.")
    value: int = Field(
        description="Centipawns from the side-to-move perspective, "
        "or number of moves until mate when type is 'mate'."
    )
    best_move: str | None = Field(
        default=None, description="Best move in UCI notation according to Stockfish."
    )
