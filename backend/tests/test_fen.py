"""Tests de la validation des positions FEN."""

import pytest

from app.services.fen import InvalidFenError, parse_fen
from tests.conftest import START_FEN


def test_parse_fen_accepts_the_starting_position():
    """La position de départ est acceptée et rendue à l'identique."""
    board = parse_fen(START_FEN)

    assert board.fen() == START_FEN


def test_parse_fen_accepts_a_position_after_a_move():
    """Une position atteinte après un coup reste valide."""
    fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"

    assert parse_fen(fen).turn is False  # trait aux Noirs


@pytest.mark.parametrize(
    "fen",
    [
        "",
        "pas une position",
        # Rangée de 9 cases : la position est syntaxiquement invalide.
        "rnbqkbnrr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        # Aucun roi sur l'échiquier : la position est illégale.
        "8/8/8/8/8/8/8/8 w - - 0 1",
    ],
)
def test_parse_fen_rejects_invalid_positions(fen):
    """Une chaîne qui ne décrit pas une position légale est rejetée."""
    with pytest.raises(InvalidFenError):
        parse_fen(fen)
