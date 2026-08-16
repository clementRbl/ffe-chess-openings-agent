"""Script d'ingestion du corpus Wikichess dans Milvus.

Lit les articles d'ouvertures (fichiers markdown), les découpe en passages
(chunking par paragraphe), les encode en vecteurs avec le modèle d'embedding,
puis (re)crée la collection Milvus et y insère les passages.

À lancer à l'intérieur du conteneur backend :
    uv run python -m app.scripts.ingest
"""

from pathlib import Path

from app.core.config import settings
from app.services.embeddings import embedding_service
from app.services.milvus_client import milvus_repository

# En dessous de ce seuil, un paragraphe isolé (ex. une ligne "ECO : B20-B99...")
# produit un embedding peu discriminant et pollue la recherche vectorielle sans
# apporter de contexte exploitable : on le fusionne avec le passage suivant.
MIN_CHUNK_CHARS = 80
# Au-delà, un passage devient trop large pour rester spécifique à une seule
# idée : on le découpe sur des frontières de mots.
MAX_CHUNK_CHARS = 600


def _merge_short_paragraphs(paragraphs: list[str]) -> list[str]:
    """Fusionne les paragraphes trop courts (< ``MIN_CHUNK_CHARS``) avec le suivant.

    Voir la vigilance de l'étape 3 des consignes : « qualité de la recherche =
    qualité des données + chunking ».
    """
    merged: list[str] = []
    pending = ""
    for paragraph in paragraphs:
        pending = f"{pending} {paragraph}".strip() if pending else paragraph
        if len(pending) >= MIN_CHUNK_CHARS:
            merged.append(pending)
            pending = ""
    if pending:
        if merged:
            merged[-1] = f"{merged[-1]} {pending}"
        else:
            merged.append(pending)
    return merged


def _split_long_paragraph(text: str) -> list[str]:
    """Découpe un paragraphe trop long (> ``MAX_CHUNK_CHARS``) sur des mots."""
    words = text.split()
    segments: list[str] = []
    current: list[str] = []
    length = 0
    for word in words:
        if current and length + len(word) + 1 > MAX_CHUNK_CHARS:
            segments.append(" ".join(current))
            current, length = [], 0
        current.append(word)
        length += len(word) + 1
    if current:
        segments.append(" ".join(current))
    return segments


def load_chunks(data_dir: Path) -> list[dict]:
    """Lit les articles markdown et les découpe en passages bornés en taille.

    Le titre de chaque passage est déduit de la première ligne de titre
    markdown (``# ...``) de l'article, sinon du nom du fichier. Les paragraphes
    trop courts sont fusionnés avec le suivant, les trop longs sont scindés
    (voir ``MIN_CHUNK_CHARS`` / ``MAX_CHUNK_CHARS``).

    Args:
        data_dir: Dossier contenant les fichiers ``.md`` du corpus.

    Returns:
        Une liste de passages de la forme ``{"title": ..., "text": ...}``.
    """
    chunks: list[dict] = []
    for path in sorted(data_dir.glob("*.md")):
        content = path.read_text(encoding="utf-8").strip()
        title = path.stem
        body = content
        if content.startswith("# "):
            first_line, _, rest = content.partition("\n")
            title = first_line[2:].strip()
            body = rest.strip()
        paragraphs = [
            " ".join(paragraph.split())
            for paragraph in body.split("\n\n")
            if paragraph.strip()
        ]
        for merged in _merge_short_paragraphs(paragraphs):
            for segment in _split_long_paragraph(merged):
                chunks.append({"title": title, "text": segment})
    return chunks


def main() -> None:
    """Charge le corpus, génère les embeddings et remplit la collection Milvus."""
    data_dir = Path(settings.wikichess_data_dir)
    chunks = load_chunks(data_dir)
    print(f"Loaded {len(chunks)} chunks from {data_dir}")

    vectors = embedding_service.embed_documents([chunk["text"] for chunk in chunks])
    rows = [
        {"vector": vector, "text": chunk["text"], "title": chunk["title"]}
        for chunk, vector in zip(chunks, vectors, strict=True)
    ]

    milvus_repository.recreate_collection()
    milvus_repository.insert(rows)
    print(f"Inserted {len(rows)} chunks into '{settings.milvus_collection}'")


if __name__ == "__main__":
    main()
