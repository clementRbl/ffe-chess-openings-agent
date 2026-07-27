"""Workflow LangGraph de l'agent d'analyse d'une position.

Orchestre l'ensemble des sources pour une position FEN donnée :

1. ``moves`` : coups théoriques (Lichess) et identification de l'ouverture ;
2. ``evaluate`` : évaluation moteur (Stockfish) ;
3. un aiguillage conditionnel choisit la suite : si une ouverture est reconnue,
   l'agent enrichit la réponse avec le contexte (Milvus) et les vidéos
   (YouTube) ; sinon il passe directement au résumé ;
4. ``summarize`` : construit une recommandation lisible ;
5. ``persist`` : enregistre l'analyse dans l'historique MongoDB.

Les appels aux API externes (Lichess, YouTube) passent par le cache MongoDB :
l'interface analyse la position à chaque coup joué, ce qui rendrait vite les
quotas insuffisants sans cette mise en cache.

Chaque nœud capture ses propres erreurs dans l'état (``sources``) afin que la
panne d'un service n'interrompe pas toute l'analyse (dégradation gracieuse).
"""

from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.graph.cache import cache_get, cache_set
from app.schemas.agent import SourceStatus
from app.schemas.chess import MovesResponse
from app.schemas.video import VideoResult
from app.services.embeddings import embedding_service
from app.services.lichess import LichessError, lichess_service
from app.services.milvus_client import MilvusError, milvus_repository
from app.services.mongo import MongoError, mongo_repository
from app.services.notation import to_french_san
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
    """Nœud : récupère les coups théoriques et identifie l'ouverture (Lichess).

    La réponse de Lichess est mise en cache dans MongoDB : une même position
    revient très souvent d'une partie à l'autre (c'est le principe même des
    ouvertures).
    """
    cache_key = f"lichess:{state['fen']}"
    cached, mongo_status = await cache_get(cache_key)
    if cached is not None:
        response = MovesResponse.model_validate(cached)
    else:
        try:
            response = await lichess_service.get_theoretical_moves(state["fen"])
        except LichessError as exc:
            return {
                "theoretical_moves": [],
                "in_theory": False,
                "sources": {
                    "lichess": SourceStatus(ok=False, detail=str(exc)),
                    "mongo": mongo_status,
                },
            }
        mongo_status = await cache_set(cache_key, response.model_dump())

    return {
        "theoretical_moves": response.moves,
        "opening": response.opening,
        "in_theory": bool(response.moves),
        "sources": {"lichess": SourceStatus(), "mongo": mongo_status},
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
    """Nœud : récupère des vidéos explicatives de l'ouverture (YouTube).

    Les résultats sont mis en cache dans MongoDB : l'API YouTube Data v3 est
    soumise à un quota journalier vite atteint (100 unités par recherche).
    """
    opening = state.get("opening")
    cache_key = f"youtube:{opening}"
    cached, mongo_status = await cache_get(cache_key)
    if cached is not None:
        videos = [VideoResult.model_validate(video) for video in cached]
    else:
        try:
            videos = await run_in_threadpool(youtube_service.search, opening)
        except YouTubeError as exc:
            return {
                "videos": [],
                "sources": {
                    "youtube": SourceStatus(ok=False, detail=str(exc)),
                    "mongo": mongo_status,
                },
            }
        mongo_status = await cache_set(
            cache_key, [video.model_dump() for video in videos]
        )

    return {
        "videos": videos,
        "sources": {"youtube": SourceStatus(), "mongo": mongo_status},
    }


def _summarize(state: AgentState) -> AgentState:
    """Nœud : construit une recommandation lisible selon la source retenue."""
    if state.get("in_theory"):
        opening = state.get("opening")
        top_moves = ", ".join(
            to_french_san(move.san) for move in state["theoretical_moves"][:3]
        )
        # Lichess ne nomme pas toujours l'ouverture (la position de départ, par
        # exemple) : on adapte la phrase plutôt que d'afficher un nom vide.
        intro = (
            f"Position dans la théorie ({opening})."
            if opening
            else "Position connue de la théorie."
        )
        summary = f"{intro} Coups principaux recommandés : {top_moves}."
    else:
        evaluation = state.get("evaluation")
        best_move = evaluation.best_move if evaluation else None
        if best_move:
            # Le moteur s'exprime en notation UCI (case de départ, case
            # d'arrivée) : on l'écrit explicitement plutôt que de laisser
            # « g1f3 » brut au lecteur.
            summary = (
                "Position hors théorie : suivez l'évaluation du moteur. "
                f"Coup suggéré : {best_move[:2]} vers {best_move[2:4]}."
            )
        else:
            summary = "Position hors théorie."
    return {"summary": summary}


async def _persist(state: AgentState) -> AgentState:
    """Nœud : enregistre l'analyse dans l'historique MongoDB.

    L'historique sert à la démonstration (montrer ce que l'agent a répondu) et
    constitue un jeu de positions annotées réutilisable par la suite. Un échec
    d'écriture est signalé dans ``sources`` mais ne fait pas échouer l'analyse.
    """
    evaluation = state.get("evaluation")
    document = {
        "fen": state["fen"],
        "opening": state.get("opening"),
        "in_theory": state.get("in_theory", False),
        "theoretical_moves": [
            move.san for move in state.get("theoretical_moves", [])[:3]
        ],
        "evaluation": evaluation.model_dump() if evaluation else None,
        "summary": state.get("summary", ""),
    }
    try:
        await mongo_repository.save_analysis(document)
        return {"sources": {"mongo": SourceStatus()}}
    except MongoError as exc:
        return {"sources": {"mongo": SourceStatus(ok=False, detail=str(exc))}}


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
    builder.add_node("persist", _persist)

    builder.add_edge(START, "moves")
    builder.add_edge("moves", "evaluate")
    builder.add_conditional_edges(
        "evaluate", _route_after_evaluate, ["context", "summarize"]
    )
    builder.add_edge("context", "videos")
    builder.add_edge("videos", "summarize")
    builder.add_edge("summarize", "persist")
    builder.add_edge("persist", END)
    return builder.compile()


agent_graph = build_agent_graph()
