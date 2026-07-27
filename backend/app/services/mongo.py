"""Accès à la base de données MongoDB.

Encapsule les deux usages de MongoDB dans le POC :

1. un **cache** des réponses des API externes (Lichess, YouTube), qui expire
   automatiquement grâce à un index TTL — l'interface interroge l'agent à chaque
   coup joué, ce cache évite donc de consommer inutilement les quotas ;
2. un **historique** des analyses produites par l'agent, utile pour la
   démonstration et pour constituer un jeu de données de positions annotées.

Comme pour Milvus, la connexion est établie à la demande (lazy) et toutes les
erreurs du driver sont converties en une exception métier unique.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from pymongo import AsyncMongoClient
from pymongo.errors import PyMongoError

from app.core.config import settings


class MongoError(Exception):
    """Levée lorsque MongoDB est injoignable ou renvoie une erreur."""


class MongoRepository:
    """Enveloppe autour du client MongoDB (cache des API et historique)."""

    def __init__(
        self,
        uri: str | None = None,
        database: str | None = None,
        cache_ttl_seconds: int | None = None,
    ) -> None:
        """Initialise le dépôt.

        Args:
            uri: URI de connexion à MongoDB (par défaut celle de la config).
            database: Nom de la base (par défaut celui de la config).
            cache_ttl_seconds: Durée de vie des entrées de cache en secondes
                (par défaut celle de la config).
        """
        self._uri = uri or settings.mongo_uri
        self._database = database or settings.mongo_database
        self._cache_ttl_seconds = (
            cache_ttl_seconds
            if cache_ttl_seconds is not None
            else settings.mongo_cache_ttl_seconds
        )
        self._client: AsyncMongoClient | None = None
        self._indexes_ready = False

    @property
    def client(self) -> AsyncMongoClient:
        """Client MongoDB, créé à la première utilisation (lazy)."""
        if self._client is None:
            try:
                self._client = AsyncMongoClient(
                    self._uri,
                    serverSelectionTimeoutMS=settings.mongo_timeout_ms,
                )
            except PyMongoError as exc:
                raise MongoError(f"Cannot connect to MongoDB: {exc}") from exc
        return self._client

    @property
    def _cache_collection(self):
        """Collection des réponses d'API mises en cache."""
        return self.client[self._database][settings.mongo_cache_collection]

    @property
    def _analyses_collection(self):
        """Collection de l'historique des analyses de l'agent."""
        return self.client[self._database][settings.mongo_analyses_collection]

    async def _ensure_indexes(self) -> None:
        """Crée les index nécessaires (une seule fois par processus).

        L'index TTL sur ``expires_at`` laisse MongoDB purger lui-même les
        entrées de cache périmées.
        """
        if self._indexes_ready:
            return
        await self._cache_collection.create_index("key", unique=True)
        await self._cache_collection.create_index("expires_at", expireAfterSeconds=0)
        await self._analyses_collection.create_index("created_at")
        self._indexes_ready = True

    async def get_cached(self, key: str) -> Any | None:
        """Renvoie la valeur en cache pour une clé, ou ``None`` si absente.

        La date d'expiration est également vérifiée à la lecture : la purge TTL
        de MongoDB n'est pas immédiate (elle s'exécute périodiquement).

        Args:
            key: Clé de cache (ex. ``"lichess:<fen>"``).

        Raises:
            MongoError: si MongoDB est injoignable ou échoue.
        """
        try:
            await self._ensure_indexes()
            document = await self._cache_collection.find_one(
                {"key": key, "expires_at": {"$gt": datetime.now(UTC)}}
            )
        except PyMongoError as exc:
            raise MongoError(f"MongoDB cache read failed: {exc}") from exc
        return document["payload"] if document else None

    async def set_cached(self, key: str, payload: Any) -> None:
        """Enregistre (ou remplace) une valeur en cache pour une clé.

        Args:
            key: Clé de cache.
            payload: Valeur à conserver (doit être sérialisable en BSON).

        Raises:
            MongoError: si MongoDB est injoignable ou échoue.
        """
        expires_at = datetime.now(UTC) + timedelta(seconds=self._cache_ttl_seconds)
        try:
            await self._ensure_indexes()
            await self._cache_collection.replace_one(
                {"key": key},
                {"key": key, "payload": payload, "expires_at": expires_at},
                upsert=True,
            )
        except PyMongoError as exc:
            raise MongoError(f"MongoDB cache write failed: {exc}") from exc

    async def save_analysis(self, document: dict) -> None:
        """Ajoute une analyse de l'agent à l'historique.

        Args:
            document: Analyse à conserver (la date de création est ajoutée).

        Raises:
            MongoError: si MongoDB est injoignable ou échoue.
        """
        try:
            await self._ensure_indexes()
            await self._analyses_collection.insert_one(
                {**document, "created_at": datetime.now(UTC)}
            )
        except PyMongoError as exc:
            raise MongoError(f"MongoDB history write failed: {exc}") from exc


mongo_repository = MongoRepository()
