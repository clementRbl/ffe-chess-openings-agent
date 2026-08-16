"""Point d'entrée de l'application FastAPI.

Ce fichier crée l'instance FastAPI et enregistre l'ensemble des routes de l'API
(versionnées sous le préfixe ``/api/v1``) : sonde de santé, coups théoriques
(Lichess), évaluation moteur (Stockfish) et recherche vectorielle (RAG Milvus).

Il configure aussi l'observabilité du service : logs JSON structurés, métriques
Prometheus (``/metrics``) et traçage best-effort des analyses dans MLflow — voir
``docs/architecture.md`` § Observabilité.
"""

import logging
import time

from fastapi import FastAPI, Request
from prometheus_fastapi_instrumentator import Instrumentator

from app.api.v1.analyze import router as analyze_router
from app.api.v1.evaluate import router as evaluate_router
from app.api.v1.health import router as health_router
from app.api.v1.moves import router as moves_router
from app.api.v1.vector_search import router as vector_search_router
from app.api.v1.videos import router as videos_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.core.tracking import configure_tracking

configure_logging()
configure_tracking()

request_logger = logging.getLogger("app.request")

app = FastAPI(title=settings.app_name)

Instrumentator().instrument(app).expose(app, endpoint="/metrics")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Journalise chaque requête HTTP (méthode, chemin, statut, durée)."""
    started_at = time.perf_counter()
    response = await call_next(request)
    request_logger.info(
        "http_request",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round((time.perf_counter() - started_at) * 1000, 1),
        },
    )
    return response


# Enregistrement des routeurs de l'API, tous préfixés par /api/v1.
app.include_router(health_router, prefix=settings.api_v1_prefix)
app.include_router(moves_router, prefix=settings.api_v1_prefix)
app.include_router(evaluate_router, prefix=settings.api_v1_prefix)
app.include_router(vector_search_router, prefix=settings.api_v1_prefix)
app.include_router(videos_router, prefix=settings.api_v1_prefix)
app.include_router(analyze_router, prefix=settings.api_v1_prefix)


@app.get("/")
def root() -> dict[str, str]:
    """Route racine renvoyant un court message de bienvenue de l'API."""
    return {"message": "FFE Chess Openings Agent API"}
