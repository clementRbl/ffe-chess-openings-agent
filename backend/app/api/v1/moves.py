"""Route des coups théoriques d'une position.

Expose ``GET /moves/{fen}`` : valide la position FEN reçue puis interroge
l'explorateur d'ouvertures Lichess pour renvoyer les coups théoriques (issus des
parties de référence) disponibles depuis cette position.
"""

from fastapi import APIRouter, HTTPException

from app.schemas.chess import MovesResponse
from app.services.fen import InvalidFenError, parse_fen
from app.services.lichess import LichessError, lichess_service

router = APIRouter(tags=["moves"])


@router.get("/moves/{fen:path}", response_model=MovesResponse)
async def get_moves(fen: str) -> MovesResponse:
    """Renvoie les coups théoriques d'une position via l'explorateur Lichess.

    Args:
        fen: Position au format FEN (les espaces doivent être encodés en ``%20``).

    Raises:
        HTTPException: 400 si la FEN est invalide, 502 en cas d'erreur Lichess.
    """
    try:
        parse_fen(fen)
    except InvalidFenError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid FEN: {exc}") from exc

    try:
        return await lichess_service.get_theoretical_moves(fen)
    except LichessError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
