"""Configuration du logging structuré (JSON) de l'application.

Chaque ligne de log est un objet JSON (un champ par information : ``level``,
``logger``, ``message``, et les champs additionnels passés via ``extra``)
plutôt qu'une phrase en texte libre. Cela permet de filtrer les journaux
(``docker compose logs backend``) sur un champ précis — par exemple tous les
échecs d'un nœud du graphe — sans dépendre d'un format de message stable.
"""

import logging
import sys

from pythonjsonlogger.json import JsonFormatter

from app.core.config import settings


def configure_logging() -> None:
    """Configure le logger racine pour émettre du JSON sur la sortie standard."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        JsonFormatter(
            "{asctime}{name}{levelname}{message}",
            style="{",
            rename_fields={
                "asctime": "timestamp",
                "levelname": "level",
                "name": "logger",
            },
        )
    )

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(settings.log_level)

    # Les bibliothèques HTTP tierces (httpx, urllib3 via googleapiclient) sont
    # très verbeuses en DEBUG : elles suivraient sinon le niveau de la racine.
    logging.getLogger("httpx").setLevel("WARNING")
    logging.getLogger("googleapiclient").setLevel("WARNING")
