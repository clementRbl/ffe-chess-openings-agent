"""Route d'analyse complète d'une position par l'agent.

Expose ``GET /analyze/{fen}`` : valide la position FEN puis déclenche le workflow
LangGraph de l'agent, qui agrège coups théoriques, évaluation moteur, contexte
et vidéos en une recommandation unique.
"""

from fastapi import APIRouter, HTTPException

from app.graph.agent_graph import agent_graph
from app.schemas.agent import AgentAnalysis
from app.services.fen import InvalidFenError, parse_fen

router = APIRouter(tags=["agent"])


@router.get("/analyze/{fen:path}", response_model=AgentAnalysis)
async def analyze(fen: str) -> AgentAnalysis:
    """Renvoie la recommandation complète de l'agent pour une position.

    Args:
        fen: Position au format FEN (les espaces doivent être encodés en ``%20``).

    Raises:
        HTTPException: 400 si la FEN est invalide.
    """
    try:
        parse_fen(fen)
    except InvalidFenError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid FEN: {exc}") from exc

    state = await agent_graph.ainvoke({"fen": fen, "sources": {}})
    return AgentAnalysis(
        fen=fen,
        opening=state.get("opening"),
        in_theory=state.get("in_theory", False),
        theoretical_moves=state.get("theoretical_moves", []),
        evaluation=state.get("evaluation"),
        context=state.get("context", []),
        videos=state.get("videos", []),
        summary=state.get("summary", ""),
        sources=state.get("sources", {}),
    )
