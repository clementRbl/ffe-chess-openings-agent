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


def _to_white_perspective(value: int, fen: str) -> int:
    """Ramène un score du point de vue du camp au trait à celui des Blancs.

    Les moteurs UCI, Stockfish compris, expriment leur évaluation du point de
    vue du joueur qui a le trait : sur une position où les Blancs ont une dame
    de plus mais où les Noirs jouent, le moteur renvoie une valeur négative.
    Cette convention est peu lisible pour un consommateur de l'API — d'autant
    que le trait change à chaque coup. On la ramène donc à la convention
    d'affichage habituelle : positif = avantage aux Blancs.

    Args:
        value: Score renvoyé par le moteur (centipions ou nombre de coups
            avant mat).
        fen: Position évaluée, dont le second champ porte le trait.

    Returns:
        Le score du point de vue des Blancs.
    """
    black_to_move = fen.split()[1] == "b"
    return -value if black_to_move else value


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
            L'évaluation (centipions ou mat) et le meilleur coup, ramenés au
            point de vue des Blancs.

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
            value=_to_white_perspective(evaluation["value"], fen),
            best_move=best_move,
        )


stockfish_service = StockfishService()
