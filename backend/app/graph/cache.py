"""Accès au cache MongoDB depuis les workflows LangGraph.

Ces deux utilitaires enveloppent le dépôt MongoDB pour l'usage particulier des
graphes : une panne du cache ne doit jamais interrompre un workflow. L'erreur
n'est pas ignorée pour autant — elle est renvoyée sous forme de ``SourceStatus``
que les nœuds placent dans l'état, et qui remonte donc jusqu'à la réponse de
l'API. Toute dégradation est en outre tracée dans les journaux du service.
"""

import logging
from typing import Any

from app.schemas.agent import SourceStatus
from app.services.mongo import MongoError, mongo_repository

logger = logging.getLogger(__name__)


async def cache_get(key: str) -> tuple[Any | None, SourceStatus]:
    """Lit une entrée du cache.

    Args:
        key: Clé de cache (ex. ``"lichess:<fen>"``).

    Returns:
        La valeur en cache (``None`` si absente ou si le cache est indisponible)
        et l'état de la source MongoDB.
    """
    try:
        return await mongo_repository.get_cached(key), SourceStatus()
    except MongoError as exc:
        logger.warning("Cache MongoDB indisponible en lecture (%s) : %s", key, exc)
        return None, SourceStatus(ok=False, detail=str(exc))


async def cache_set(key: str, payload: Any) -> SourceStatus:
    """Écrit une entrée dans le cache.

    Args:
        key: Clé de cache.
        payload: Valeur à conserver.

    Returns:
        L'état de la source MongoDB après l'écriture.
    """
    try:
        await mongo_repository.set_cached(key, payload)
        return SourceStatus()
    except MongoError as exc:
        logger.warning("Cache MongoDB indisponible en écriture (%s) : %s", key, exc)
        return SourceStatus(ok=False, detail=str(exc))
