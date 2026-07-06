"""Service de génération d'embeddings.

Encapsule le modèle ``sentence-transformers`` (Qwen3-Embedding-0.6B) utilisé pour
transformer les textes en vecteurs. Le modèle est chargé une seule fois, à la
demande (lazy), afin d'éviter un démarrage lent et une consommation mémoire
inutile tant qu'aucun embedding n'est requis.
"""

from functools import lru_cache

from sentence_transformers import SentenceTransformer

from app.core.config import settings


@lru_cache(maxsize=1)
def _get_model() -> SentenceTransformer:
    """Charge le modèle d'embedding une seule fois et le garde en mémoire."""
    return SentenceTransformer(settings.embedding_model)


class EmbeddingService:
    """Génère des embeddings avec un modèle sentence-transformers.

    Les documents et les requêtes sont encodés légèrement différemment : les
    modèles d'embedding Qwen3 attendent une instruction (« prompt ») côté requête
    pour améliorer la qualité de la recherche.
    """

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Encode une liste de documents en vecteurs normalisés."""
        model = _get_model()
        vectors = model.encode(texts, normalize_embeddings=True)
        return vectors.tolist()

    def embed_query(self, text: str) -> list[float]:
        """Encode une requête en un vecteur normalisé.

        Utilise le prompt « query » du modèle s'il existe, sinon encode le texte
        tel quel.
        """
        model = _get_model()
        try:
            vectors = model.encode(
                [text], prompt_name="query", normalize_embeddings=True
            )
        except ValueError:
            # Modèle sans prompt « query » prédéfini : encodage simple.
            vectors = model.encode([text], normalize_embeddings=True)
        return vectors[0].tolist()


embedding_service = EmbeddingService()
