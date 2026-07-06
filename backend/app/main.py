"""Point d'entrée de l'application FastAPI.

Ce fichier crée l'instance FastAPI et enregistre l'ensemble des routes de l'API
(versionnées sous le préfixe ``/api/v1``) : sonde de santé, coups théoriques
(Lichess), évaluation moteur (Stockfish) et recherche vectorielle (RAG Milvus).
"""

from fastapi import FastAPI

from app.api.v1.evaluate import router as evaluate_router
from app.api.v1.health import router as health_router
from app.api.v1.moves import router as moves_router
from app.api.v1.vector_search import router as vector_search_router
from app.api.v1.videos import router as videos_router
from app.core.config import settings

app = FastAPI(title=settings.app_name)

# Enregistrement des routeurs de l'API, tous préfixés par /api/v1.
app.include_router(health_router, prefix=settings.api_v1_prefix)
app.include_router(moves_router, prefix=settings.api_v1_prefix)
app.include_router(evaluate_router, prefix=settings.api_v1_prefix)
app.include_router(vector_search_router, prefix=settings.api_v1_prefix)
app.include_router(videos_router, prefix=settings.api_v1_prefix)


@app.get("/")
def root() -> dict[str, str]:
    """Route racine renvoyant un court message de bienvenue de l'API."""
    return {"message": "FFE Chess Openings Agent API"}
