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


def load_chunks(data_dir: Path) -> list[dict]:
    """Lit les articles markdown et les découpe en passages (paragraphes).

    Le titre de chaque passage est déduit de la première ligne de titre
    markdown (``# ...``) de l'article, sinon du nom du fichier.

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
        for paragraph in body.split("\n\n"):
            text = " ".join(paragraph.split())
            if text:
                chunks.append({"title": title, "text": text})
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
