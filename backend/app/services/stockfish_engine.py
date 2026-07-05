from stockfish import Stockfish

from app.core.config import settings
from app.schemas.chess import EvaluationResponse


class StockfishError(Exception):
    """Raised when the Stockfish engine is unavailable or fails to evaluate."""


class StockfishService:
    """Wrapper around the Stockfish engine for position evaluation."""

    def __init__(
        self,
        path: str | None = None,
        depth: int | None = None,
    ) -> None:
        self._path = path or settings.stockfish_path
        self._depth = depth or settings.stockfish_depth

    def evaluate(self, fen: str) -> EvaluationResponse:
        """Evaluate a position with Stockfish.

        The position is assumed to be a valid FEN (validated upstream).

        Raises:
            StockfishError: if the engine binary is missing or evaluation fails.
        """
        try:
            engine = Stockfish(
                path=self._path,
                depth=self._depth,
                parameters={
                    "Threads": settings.stockfish_threads,
                    "Hash": settings.stockfish_hash_mb,
                },
            )
            engine.set_fen_position(fen)
            evaluation = engine.get_evaluation()
            best_move = engine.get_best_move()
        except (FileNotFoundError, OSError) as exc:
            raise StockfishError(f"Stockfish engine unavailable: {exc}") from exc
        except Exception as exc:  # noqa: BLE001 - surface engine errors uniformly
            raise StockfishError(f"Stockfish evaluation failed: {exc}") from exc

        return EvaluationResponse(
            fen=fen,
            type=evaluation["type"],
            value=evaluation["value"],
            best_move=best_move,
        )


stockfish_service = StockfishService()
