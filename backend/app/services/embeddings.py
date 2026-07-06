from functools import lru_cache

from sentence_transformers import SentenceTransformer

from app.core.config import settings


@lru_cache(maxsize=1)
def _get_model() -> SentenceTransformer:
    """Load the embedding model once and keep it in memory (lazy)."""
    return SentenceTransformer(settings.embedding_model)


class EmbeddingService:
    """Generate embeddings with a sentence-transformers model.

    Documents and queries are encoded slightly differently: Qwen3 embedding
    models expect an instruction prompt on the query side for best retrieval.
    """

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        model = _get_model()
        vectors = model.encode(texts, normalize_embeddings=True)
        return vectors.tolist()

    def embed_query(self, text: str) -> list[float]:
        model = _get_model()
        try:
            vectors = model.encode(
                [text], prompt_name="query", normalize_embeddings=True
            )
        except ValueError:
            # Model without a predefined "query" prompt: encode plainly.
            vectors = model.encode([text], normalize_embeddings=True)
        return vectors[0].tolist()


embedding_service = EmbeddingService()
