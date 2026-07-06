from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.core.config import settings
from app.services.embeddings import embedding_service
from app.services.milvus_client import milvus_repository


class VectorSearchState(TypedDict, total=False):
    """State passed between the nodes of the vector-search graph."""

    query: str
    top_k: int
    query_vector: list[float]
    results: list[dict]


def _embed_query(state: VectorSearchState) -> VectorSearchState:
    return {"query_vector": embedding_service.embed_query(state["query"])}


def _search(state: VectorSearchState) -> VectorSearchState:
    top_k = state.get("top_k") or settings.vector_search_top_k
    results = milvus_repository.search(state["query_vector"], top_k)
    return {"results": results}


def build_vector_search_graph():
    """Build the LangGraph workflow: embed the query, then search Milvus."""
    builder = StateGraph(VectorSearchState)
    builder.add_node("embed_query", _embed_query)
    builder.add_node("search", _search)
    builder.add_edge(START, "embed_query")
    builder.add_edge("embed_query", "search")
    builder.add_edge("search", END)
    return builder.compile()


vector_search_graph = build_vector_search_graph()
