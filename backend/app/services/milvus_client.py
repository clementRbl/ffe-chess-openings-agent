from pymilvus import MilvusClient

from app.core.config import settings


class MilvusError(Exception):
    """Raised when the Milvus vector database is unavailable or fails."""


class MilvusRepository:
    """Thin wrapper around the Milvus client for the openings collection."""

    def __init__(
        self,
        uri: str | None = None,
        collection: str | None = None,
        dim: int | None = None,
    ) -> None:
        self._uri = uri or settings.milvus_uri
        self._collection = collection or settings.milvus_collection
        self._dim = dim or settings.embedding_dim
        self._client: MilvusClient | None = None

    @property
    def client(self) -> MilvusClient:
        if self._client is None:
            try:
                self._client = MilvusClient(uri=self._uri)
            except Exception as exc:  # noqa: BLE001
                raise MilvusError(f"Cannot connect to Milvus: {exc}") from exc
        return self._client

    def recreate_collection(self) -> None:
        """Drop and create the openings collection (used by ingestion)."""
        if self.client.has_collection(self._collection):
            self.client.drop_collection(self._collection)
        self.client.create_collection(
            collection_name=self._collection,
            dimension=self._dim,
            metric_type="COSINE",
            auto_id=True,
        )

    def insert(self, rows: list[dict]) -> None:
        """Insert rows shaped as {vector, text, title}."""
        self.client.insert(collection_name=self._collection, data=rows)

    def search(self, query_vector: list[float], top_k: int) -> list[dict]:
        """Return the top_k most similar chunks with their metadata."""
        try:
            results = self.client.search(
                collection_name=self._collection,
                data=[query_vector],
                limit=top_k,
                output_fields=["text", "title"],
            )
        except Exception as exc:  # noqa: BLE001
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
