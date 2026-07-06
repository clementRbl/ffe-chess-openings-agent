"""Workflow LangGraph de recherche vectorielle.

Définit un graphe LangGraph simple à deux étapes : encodage de la requête en
vecteur, puis recherche des passages les plus proches dans Milvus. Ce graphe
constitue la première brique d'orchestration de l'agent ; il pourra être enrichi
ultérieurement (choix d'outils, appel LLM, etc.).
"""

from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.core.config import settings
from app.services.embeddings import embedding_service
from app.services.milvus_client import milvus_repository


class VectorSearchState(TypedDict, total=False):
    """État transmis entre les nœuds du graphe de recherche vectorielle.

    Attributes:
        query: Requête textuelle de l'utilisateur.
        top_k: Nombre de passages souhaités.
        query_vector: Vecteur de la requête (produit par le nœud d'embedding).
        results: Passages récupérés (produits par le nœud de recherche).
    """

    query: str
    top_k: int
    query_vector: list[float]
    results: list[dict]


def _embed_query(state: VectorSearchState) -> VectorSearchState:
    """Nœud 1 : encode la requête en un vecteur."""
    return {"query_vector": embedding_service.embed_query(state["query"])}


def _search(state: VectorSearchState) -> VectorSearchState:
    """Nœud 2 : recherche les passages les plus proches dans Milvus."""
    top_k = state.get("top_k") or settings.vector_search_top_k
    results = milvus_repository.search(state["query_vector"], top_k)
    return {"results": results}


def build_vector_search_graph():
    """Construit et compile le graphe : ``embed_query`` puis ``search``."""
    builder = StateGraph(VectorSearchState)
    builder.add_node("embed_query", _embed_query)
    builder.add_node("search", _search)
    builder.add_edge(START, "embed_query")
    builder.add_edge("embed_query", "search")
    builder.add_edge("search", END)
    return builder.compile()


vector_search_graph = build_vector_search_graph()
