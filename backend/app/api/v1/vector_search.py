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
    """Return relevant Wikichess passages for an opening via vector search.

    The retrieval is orchestrated by the LangGraph workflow (embed then search).
    """
    try:
        state = await run_in_threadpool(
            vector_search_graph.invoke, {"query": query, "top_k": top_k}
        )
    except MilvusError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return VectorSearchResponse(query=query, results=state.get("results", []))
