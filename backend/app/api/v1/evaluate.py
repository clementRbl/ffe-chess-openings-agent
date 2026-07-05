from fastapi import APIRouter, HTTPException
from starlette.concurrency import run_in_threadpool

from app.schemas.chess import EvaluationResponse
from app.services.fen import InvalidFenError, parse_fen
from app.services.stockfish_engine import StockfishError, stockfish_service

router = APIRouter(tags=["evaluate"])


@router.get("/evaluate/{fen:path}", response_model=EvaluationResponse)
async def evaluate_position(fen: str) -> EvaluationResponse:
    """Return the Stockfish evaluation of a position (in centipawns or mate)."""
    try:
        parse_fen(fen)
    except InvalidFenError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid FEN: {exc}") from exc

    try:
        return await run_in_threadpool(stockfish_service.evaluate, fen)
    except StockfishError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
