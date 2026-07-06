"""Workflow LangGraph de recherche de vidéos explicatives.

Définit un graphe LangGraph à deux étapes : construction d'une requête de
recherche ciblée à partir du nom de l'ouverture, puis appel à l'API YouTube pour
récupérer les vidéos pertinentes. Ce graphe permet à l'agent de proposer
automatiquement des ressources vidéo.
"""

from typing import TypedDict

from langgraph.graph import END, START, StateGraph

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


def _fetch_videos(state: VideosState) -> VideosState:
    """Nœud 2 : interroge l'API YouTube pour récupérer les vidéos."""
    return {"videos": youtube_service.search(state["opening"])}


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
