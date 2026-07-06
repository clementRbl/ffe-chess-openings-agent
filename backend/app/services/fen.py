"""Validation des positions FEN.

Fournit un utilitaire qui s'appuie sur ``python-chess`` pour vérifier qu'une
chaîne FEN décrit bien une position légale, avant tout appel aux services
externes (Lichess, Stockfish).
"""

import chess


class InvalidFenError(ValueError):
    """Levée lorsqu'une chaîne FEN ne décrit pas une position d'échecs valide."""


def parse_fen(fen: str) -> chess.Board:
    """Valide une chaîne FEN et renvoie l'échiquier correspondant.

    Args:
        fen: Position au format FEN.

    Returns:
        L'échiquier ``chess.Board`` construit à partir de la FEN.

    Raises:
        InvalidFenError: si la FEN est malformée ou décrit une position illégale.
    """
    try:
        return chess.Board(fen)
    except ValueError as exc:
        raise InvalidFenError(str(exc)) from exc
