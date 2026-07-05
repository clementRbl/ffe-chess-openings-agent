from fastapi import APIRouter, HTTPException

from app.schemas.chess import MovesResponse
from app.services.fen import InvalidFenError, parse_fen
from app.services.lichess import LichessError, lichess_service

router = APIRouter(tags=["moves"])


@router.get("/moves/{fen:path}", response_model=MovesResponse)
async def get_moves(fen: str) -> MovesResponse:
    """Return the theoretical moves for a position from the Lichess explorer."""
    try:
        parse_fen(fen)
    except InvalidFenError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid FEN: {exc}") from exc

    try:
        return await lichess_service.get_theoretical_moves(fen)
    except LichessError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
