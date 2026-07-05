import chess


class InvalidFenError(ValueError):
    """Raised when a FEN string is not a valid chess position."""


def parse_fen(fen: str) -> chess.Board:
    """Validate a FEN string and return the corresponding board.

    Raises:
        InvalidFenError: if the FEN is malformed or describes an illegal
            position.
    """
    try:
        return chess.Board(fen)
    except ValueError as exc:
        raise InvalidFenError(str(exc)) from exc
