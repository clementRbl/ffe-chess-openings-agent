"""Route de vérification de l'état du service (healthcheck).

Utilisée pour s'assurer que le conteneur du backend a démarré et répond
correctement (sonde de disponibilité pour Docker ou un orchestrateur).
"""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/healthcheck")
def healthcheck() -> dict[str, str]:
    """Renvoie un statut ``ok`` confirmant que le service est opérationnel."""
    return {"status": "ok"}
