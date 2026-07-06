"""Preprocess the Wikichess corpus, embed it and load it into Milvus.

Run inside the backend container:
    uv run python -m app.scripts.ingest
"""

from pathlib import Path

from app.core.config import settings
from app.services.embeddings import embedding_service
from app.services.milvus_client import milvus_repository


def load_chunks(data_dir: Path) -> list[dict]:
    """Read markdown articles and split them into paragraph-level chunks."""
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
