"""Workflow LangGraph de l'agent d'analyse d'une position.

Orchestre l'ensemble des sources pour une position FEN donnée :

1. ``moves`` : coups théoriques (Lichess) et identification de l'ouverture ;
2. ``evaluate`` : évaluation moteur (Stockfish) ;
3. un aiguillage conditionnel choisit la suite : si une ouverture est reconnue,
   l'agent enrichit la réponse avec le contexte (Milvus) et les vidéos
   (YouTube) ; sinon il passe directement au résumé ;
4. ``summarize`` : construit une recommandation lisible.

Chaque nœud capture ses propres erreurs dans l'état (``sources``) afin que la
panne d'un service n'interrompe pas toute l'analyse (dégradation gracieuse).
"""

from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.schemas.agent import SourceStatus
from app.services.embeddings import embedding_service
from app.services.lichess import LichessError, lichess_service
from app.services.milvus_client import MilvusError, milvus_repository
from app.services.stockfish_engine import StockfishError, stockfish_service
from app.services.youtube import YouTubeError, youtube_service


def _merge_sources(current: dict, update: dict) -> dict:
    """Réducteur fusionnant les états de sources produits par chaque nœud."""
    return {**current, **update}


class AgentState(TypedDict, total=False):
    """État partagé entre les nœuds du graphe de l'agent."""

    fen: str
    opening: str | None
    in_theory: bool
    theoretical_moves: list
    evaluation: object
    context: list
    videos: list
    summary: str
    sources: Annotated[dict, _merge_sources]


async def _moves(state: AgentState) -> AgentState:
    """Nœud : récupère les coups théoriques et identifie l'ouverture (Lichess)."""
    try:
        response = await lichess_service.get_theoretical_moves(state["fen"])
        return {
            "theoretical_moves": response.moves,
            "opening": response.opening,
            "in_theory": bool(response.moves),
            "sources": {"lichess": SourceStatus()},
        }
    except LichessError as exc:
        return {
            "theoretical_moves": [],
            "in_theory": False,
            "sources": {"lichess": SourceStatus(ok=False, detail=str(exc))},
        }


async def _evaluate(state: AgentState) -> AgentState:
    """Nœud : évalue la position avec Stockfish."""
    try:
        evaluation = await run_in_threadpool(stockfish_service.evaluate, state["fen"])
        return {"evaluation": evaluation, "sources": {"stockfish": SourceStatus()}}
    except StockfishError as exc:
        return {"sources": {"stockfish": SourceStatus(ok=False, detail=str(exc))}}


async def _context(state: AgentState) -> AgentState:
    """Nœud : récupère le contexte textuel de l'ouverture (Milvus)."""
    query = state.get("opening") or "chess opening"
    try:
        vector = await run_in_threadpool(embedding_service.embed_query, query)
        results = await run_in_threadpool(
            milvus_repository.search, vector, settings.vector_search_top_k
        )
        return {"context": results, "sources": {"milvus": SourceStatus()}}
    except MilvusError as exc:
        return {
            "context": [],
            "sources": {"milvus": SourceStatus(ok=False, detail=str(exc))},
        }


async def _videos(state: AgentState) -> AgentState:
    """Nœud : récupère des vidéos explicatives de l'ouverture (YouTube)."""
    opening = state.get("opening")
    try:
        videos = await run_in_threadpool(youtube_service.search, opening)
        return {"videos": videos, "sources": {"youtube": SourceStatus()}}
    except YouTubeError as exc:
        return {
            "videos": [],
            "sources": {"youtube": SourceStatus(ok=False, detail=str(exc))},
        }


def _summarize(state: AgentState) -> AgentState:
    """Nœud : construit une recommandation lisible selon la source retenue."""
    if state.get("in_theory"):
        opening = state.get("opening") or "cette ouverture"
        top_moves = ", ".join(move.san for move in state["theoretical_moves"][:3])
        summary = (
            f"Position dans la théorie ({opening}). "
            f"Coups principaux recommandés : {top_moves}."
        )
    else:
        evaluation = state.get("evaluation")
        best_move = evaluation.best_move if evaluation else None
        if best_move:
            summary = (
                "Position hors théorie : suivez l'évaluation du moteur. "
                f"Coup suggéré par Stockfish : {best_move}."
            )
        else:
            summary = "Position hors théorie."
    return {"summary": summary}


def _route_after_evaluate(state: AgentState) -> str:
    """Aiguillage : enrichir (contexte + vidéos) si une ouverture est reconnue."""
    return "context" if state.get("opening") else "summarize"


def build_agent_graph():
    """Construit et compile le graphe d'orchestration de l'agent."""
    builder = StateGraph(AgentState)
    builder.add_node("moves", _moves)
    builder.add_node("evaluate", _evaluate)
    builder.add_node("context", _context)
    builder.add_node("videos", _videos)
    builder.add_node("summarize", _summarize)

    builder.add_edge(START, "moves")
    builder.add_edge("moves", "evaluate")
    builder.add_conditional_edges(
        "evaluate", _route_after_evaluate, ["context", "summarize"]
    )
    builder.add_edge("context", "videos")
    builder.add_edge("videos", "summarize")
    builder.add_edge("summarize", END)
    return builder.compile()


agent_graph = build_agent_graph()
