"""Accès à la base de données vectorielle Milvus.

Encapsule le client Milvus pour la collection des ouvertures : création de la
collection, insertion des passages et recherche par similarité. Isole la
logique Milvus du reste de l'application et convertit ses erreurs en une
exception métier unique. La connexion est établie à la demande (lazy).
"""

from pymilvus import MilvusClient

from app.core.config import settings


class MilvusError(Exception):
    """Levée lorsque la base vectorielle Milvus est injoignable ou échoue."""


class MilvusRepository:
    """Enveloppe autour du client Milvus pour la collection des ouvertures."""

    def __init__(
        self,
        uri: str | None = None,
        collection: str | None = None,
        dim: int | None = None,
    ) -> None:
        """Initialise le dépôt.

        Args:
            uri: URI de connexion à Milvus (par défaut celle de la config).
            collection: Nom de la collection (par défaut celui de la config).
            dim: Dimension des vecteurs (par défaut celle de la config).
        """
        self._uri = uri or settings.milvus_uri
        self._collection = collection or settings.milvus_collection
        self._dim = dim or settings.embedding_dim
        self._client: MilvusClient | None = None

    @property
    def client(self) -> MilvusClient:
        """Client Milvus, connecté à la première utilisation (lazy)."""
        if self._client is None:
            try:
                self._client = MilvusClient(uri=self._uri)
            except Exception as exc:
                raise MilvusError(f"Cannot connect to Milvus: {exc}") from exc
        return self._client

    def recreate_collection(self) -> None:
        """Supprime puis recrée la collection des ouvertures (utilisé à l'ingestion)."""
        if self.client.has_collection(self._collection):
            self.client.drop_collection(self._collection)
        self.client.create_collection(
            collection_name=self._collection,
            dimension=self._dim,
            metric_type="COSINE",
            auto_id=True,
        )

    def insert(self, rows: list[dict]) -> None:
        """Insère des lignes de la forme ``{vector, text, title}``."""
        self.client.insert(collection_name=self._collection, data=rows)

    def search(self, query_vector: list[float], top_k: int) -> list[dict]:
        """Renvoie les ``top_k`` passages les plus proches et leurs métadonnées.

        Args:
            query_vector: Vecteur de la requête.
            top_k: Nombre de passages à renvoyer.

        Raises:
            MilvusError: si la recherche échoue.
        """
        try:
            results = self.client.search(
                collection_name=self._collection,
                data=[query_vector],
                limit=top_k,
                output_fields=["text", "title"],
            )
        except Exception as exc:
            raise MilvusError(f"Milvus search failed: {exc}") from exc

        hits = results[0] if results else []
        return [
            {
                "title": hit["entity"].get("title"),
                "text": hit["entity"].get("text"),
                "score": hit["distance"],
            }
            for hit in hits
        ]


milvus_repository = MilvusRepository()
