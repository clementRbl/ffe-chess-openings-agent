"""Suivi MLflow des exécutions de l'agent (surveillance « best effort »).

Contrairement aux sources métier (Lichess, Stockfish, Milvus, YouTube, Mongo),
le traçage MLflow n'a pas vocation à faire échouer ou dégrader une analyse :
c'est un outil de diagnostic pour le développeur, pas une donnée attendue par
l'utilisateur. Si le serveur MLflow est absent ou injoignable, on le signale
dans les journaux et l'application démarre normalement.

Le traçage est instrumenté manuellement (``mlflow.trace``, voir
``app/graph/agent_graph.py``) plutôt que via ``mlflow.langchain.autolog()`` :
cet autolog exige le paquet ``langchain`` complet (au-delà de
``langchain-core``, déjà installé par LangGraph) pour sa seule vérification de
version, ce qui ajoutait une dépendance sans rapport avec ce que ce projet
utilise réellement.
"""

import logging

import mlflow

from app.core.config import settings

logger = logging.getLogger("app.tracking")


def configure_tracking() -> None:
    """Configure la destination des traces MLflow si un serveur est configuré."""
    if not settings.mlflow_tracking_uri:
        logger.info(
            "mlflow_tracking_disabled",
            extra={"reason": "MLFLOW_TRACKING_URI is not set"},
        )
        return

    try:
        mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
        mlflow.set_experiment(settings.mlflow_experiment_name)
    except Exception:
        # Volontairement large : une panne du serveur MLflow (indisponible,
        # mal configuré) ne doit jamais empêcher le démarrage du backend ni
        # casser une analyse. L'échec est journalisé, jamais avalé en silence.
        logger.warning("mlflow_tracking_unavailable", exc_info=True)
        return

    logger.info(
        "mlflow_tracking_enabled",
        extra={
            "uri": settings.mlflow_tracking_uri,
            "experiment": settings.mlflow_experiment_name,
        },
    )
