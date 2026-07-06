"""Route de recherche de vidéos explicatives pour une ouverture.

Expose ``GET /videos/{opening}`` : déclenche le workflow LangGraph qui construit
une requête ciblée puis interroge l'API YouTube, et renvoie les vidéos
pertinentes avec leurs métadonnées (liens de visionnage et d'intégration).
"""

from fastapi import APIRouter, HTTPException
from starlette.concurrency import run_in_threadpool

from app.graph.videos_graph import videos_graph
from app.schemas.video import VideosResponse
from app.services.youtube import YouTubeError

router = APIRouter(tags=["videos"])


@router.get("/videos/{opening}", response_model=VideosResponse)
async def get_videos(opening: str) -> VideosResponse:
    """Renvoie des vidéos YouTube explicatives pour une ouverture.

    La recherche (construction de la requête puis appel YouTube) est orchestrée
    par le workflow LangGraph. L'appel réseau étant bloquant, l'invocation du
    graph est déléguée à un thread.

    Args:
        opening: Nom de l'ouverture (ex. « défense sicilienne »).

    Raises:
        HTTPException: 503 si la clé API est absente ou si l'API YouTube échoue
            (par exemple en cas de dépassement de quota).
    """
    try:
        state = await run_in_threadpool(videos_graph.invoke, {"opening": opening})
    except YouTubeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return VideosResponse(opening=opening, videos=state.get("videos", []))
