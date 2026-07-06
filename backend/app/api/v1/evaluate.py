"""Route d'évaluation d'une position par Stockfish.

Expose ``GET /evaluate/{fen}`` : valide la position FEN reçue puis demande au
moteur Stockfish son évaluation (en centipions ou en nombre de coups avant mat)
ainsi que le meilleur coup. Utile lorsque la partie sort de la théorie.
"""

from fastapi import APIRouter, HTTPException
from starlette.concurrency import run_in_threadpool

from app.schemas.chess import EvaluationResponse
from app.services.fen import InvalidFenError, parse_fen
from app.services.stockfish_engine import StockfishError, stockfish_service

router = APIRouter(tags=["evaluate"])


@router.get("/evaluate/{fen:path}", response_model=EvaluationResponse)
async def evaluate_position(fen: str) -> EvaluationResponse:
    """Renvoie l'évaluation Stockfish d'une position (centipions ou mat).

    L'appel au moteur étant bloquant, il est délégué à un thread pour ne pas
    bloquer la boucle d'événements asynchrone.

    Args:
        fen: Position au format FEN (les espaces doivent être encodés en ``%20``).

    Raises:
        HTTPException: 400 si la FEN est invalide, 503 si le moteur est
            indisponible ou échoue.
    """
    try:
        parse_fen(fen)
    except InvalidFenError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid FEN: {exc}") from exc

    try:
        return await run_in_threadpool(stockfish_service.evaluate, fen)
    except StockfishError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
