from fastapi import FastAPI

from app.api.v1.evaluate import router as evaluate_router
from app.api.v1.health import router as health_router
from app.api.v1.moves import router as moves_router
from app.core.config import settings

app = FastAPI(title=settings.app_name)

app.include_router(health_router, prefix=settings.api_v1_prefix)
app.include_router(moves_router, prefix=settings.api_v1_prefix)
app.include_router(evaluate_router, prefix=settings.api_v1_prefix)


@app.get("/")
def root() -> dict[str, str]:
    """Root endpoint returning a short welcome message."""
    return {"message": "FFE Chess Openings Agent API"}
