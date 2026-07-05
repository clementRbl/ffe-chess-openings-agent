from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/healthcheck")
def healthcheck() -> dict[str, str]:
    """Liveness probe used to verify the container is up and running."""
    return {"status": "ok"}
