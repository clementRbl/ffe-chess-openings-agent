"""Route de recherche vectorielle (RAG) sur les ouvertures.

Expose ``GET /vector-search`` : à partir d'une requête textuelle (nom d'ouverture
ou question en langage naturel), déclenche le workflow LangGraph qui encode la
requête puis interroge Milvus, et renvoie les passages Wikichess les plus
pertinents.
"""

from fastapi import APIRouter, HTTPException, Query
from starlette.concurrency import run_in_threadpool

from app.graph.vector_search_graph import vector_search_graph
from app.schemas.rag import VectorSearchResponse
from app.services.milvus_client import MilvusError

router = APIRouter(tags=["rag"])


@router.get("/vector-search", response_model=VectorSearchResponse)
async def vector_search(
    query: str = Query(..., min_length=2, description="Opening name or question."),
    top_k: int | None = Query(default=None, ge=1, le=20),
) -> VectorSearchResponse:
    """Renvoie les passages Wikichess pertinents pour une ouverture.

    La récupération (embedding de la requête puis recherche) est orchestrée par
    le workflow LangGraph. Comme les traitements sont bloquants, l'invocation du
    graph est déléguée à un thread.

    Args:
        query: Nom d'ouverture ou question en langage naturel.
        top_k: Nombre de passages à renvoyer (valeur de config par défaut).

    Raises:
        HTTPException: 503 si Milvus est indisponible ou échoue.
    """
    try:
        state = await run_in_threadpool(
            vector_search_graph.invoke, {"query": query, "top_k": top_k}
        )
    except MilvusError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return VectorSearchResponse(query=query, results=state.get("results", []))
