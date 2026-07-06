"""Service d'évaluation par le moteur Stockfish.

Encapsule l'utilisation du moteur Stockfish pour évaluer une position et
proposer le meilleur coup. Isole la logique du moteur du reste de l'application
et convertit ses erreurs en une exception métier unique.
"""

from stockfish import Stockfish

from app.core.config import settings
from app.schemas.chess import EvaluationResponse


class StockfishError(Exception):
    """Levée lorsque le moteur Stockfish est indisponible ou échoue à évaluer."""


class StockfishService:
    """Enveloppe autour du moteur Stockfish pour l'évaluation de positions."""

    def __init__(
        self,
        path: str | None = None,
        depth: int | None = None,
    ) -> None:
        """Initialise le service.

        Args:
            path: Chemin de l'exécutable Stockfish (par défaut celui de la config).
            depth: Profondeur de recherche (par défaut celle de la config).
        """
        self._path = path or settings.stockfish_path
        self._depth = depth or settings.stockfish_depth

    def evaluate(self, fen: str) -> EvaluationResponse:
        """Évalue une position avec Stockfish.

        La position est supposée être une FEN valide (validée en amont).

        Args:
            fen: Position au format FEN.

        Returns:
            L'évaluation (centipions ou mat) et le meilleur coup.

        Raises:
            StockfishError: si l'exécutable est introuvable ou si l'évaluation
                échoue.
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
        except Exception as exc:
            # On uniformise toute erreur du moteur en une exception métier.
            raise StockfishError(f"Stockfish evaluation failed: {exc}") from exc

        return EvaluationResponse(
            fen=fen,
            type=evaluation["type"],
            value=evaluation["value"],
            best_move=best_move,
        )


stockfish_service = StockfishService()
