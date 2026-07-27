"""Workflow LangGraph de recherche de vidéos explicatives.

Définit un graphe LangGraph à deux étapes : construction d'une requête de
recherche ciblée à partir du nom de l'ouverture, puis appel à l'API YouTube pour
récupérer les vidéos pertinentes. Ce graphe permet à l'agent de proposer
automatiquement des ressources vidéo.

Les résultats sont mis en cache dans MongoDB afin de préserver le quota
journalier de l'API YouTube Data v3.
"""

from typing import TypedDict

from langgraph.graph import END, START, StateGraph
from starlette.concurrency import run_in_threadpool

from app.graph.cache import cache_get, cache_set
from app.schemas.video import VideoResult
from app.services.youtube import youtube_service


class VideosState(TypedDict, total=False):
    """État transmis entre les nœuds du graphe de recherche de vidéos.

    Attributes:
        opening: Nom de l'ouverture recherchée.
        query: Requête de recherche construite (produite par le premier nœud).
        videos: Vidéos récupérées (produites par le second nœud).
    """

    opening: str
    query: str
    videos: list


def _build_query(state: VideosState) -> VideosState:
    """Nœud 1 : construit la requête de recherche à partir de l'ouverture."""
    return {"query": youtube_service.build_query(state["opening"])}


async def _fetch_videos(state: VideosState) -> VideosState:
    """Nœud 2 : renvoie les vidéos, depuis le cache MongoDB ou l'API YouTube.

    L'appel à l'API YouTube étant bloquant, il est délégué à un thread pour ne
    pas bloquer la boucle d'événements.
    """
    opening = state["opening"]
    cache_key = f"youtube:{opening}"
    cached, _ = await cache_get(cache_key)
    if cached is not None:
        return {"videos": [VideoResult.model_validate(video) for video in cached]}

    videos = await run_in_threadpool(youtube_service.search, opening)
    await cache_set(cache_key, [video.model_dump() for video in videos])
    return {"videos": videos}


def build_videos_graph():
    """Construit et compile le graphe : ``build_query`` puis ``fetch_videos``."""
    builder = StateGraph(VideosState)
    builder.add_node("build_query", _build_query)
    builder.add_node("fetch_videos", _fetch_videos)
    builder.add_edge(START, "build_query")
    builder.add_edge("build_query", "fetch_videos")
    builder.add_edge("fetch_videos", END)
    return builder.compile()


videos_graph = build_videos_graph()
