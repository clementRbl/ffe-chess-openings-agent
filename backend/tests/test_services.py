"""Tests des services métier (transformation des réponses des API externes)."""

import pytest

from app.services.lichess import LichessService
from app.services.youtube import YouTubeError, YouTubeService
from tests.conftest import START_FEN


def test_lichess_response_is_mapped_to_the_domain_model():
    """La réponse brute de Lichess est traduite en modèles de l'application."""
    payload = {
        "opening": {"name": "Sicilian Defense"},
        "moves": [
            {"uci": "e2e4", "san": "e4", "white": 100, "draws": 50, "black": 40},
            {"uci": "d2d4", "san": "d4", "white": 80, "draws": 60, "black": 30},
        ],
    }

    response = LichessService._parse(START_FEN, payload)

    assert response.opening == "Sicilian Defense"
    assert [move.san for move in response.moves] == ["e4", "d4"]
    # Le total est recalculé à partir des trois issues possibles.
    assert response.moves[0].total == 190


def test_lichess_response_without_opening_is_supported():
    """Une position inconnue de la théorie ne renvoie ni ouverture ni coup."""
    response = LichessService._parse(START_FEN, {"opening": None, "moves": []})

    assert response.opening is None
    assert response.moves == []


def test_youtube_query_combines_opening_and_keywords():
    """La requête de recherche associe l'ouverture aux mots-clés configurés."""
    service = YouTubeService(api_key="test-key", keywords="chess opening tutorial")

    assert service.build_query("sicilienne") == "sicilienne chess opening tutorial"


def test_youtube_requires_an_api_key():
    """Sans clé API, le service échoue explicitement plutôt qu'en silence."""
    service = YouTubeService(api_key="")

    with pytest.raises(YouTubeError, match="YOUTUBE_API_KEY"):
        service.search("sicilienne")


def test_youtube_response_is_mapped_and_incomplete_items_are_ignored():
    """Les vidéos sont converties et les entrées sans identifiant écartées."""
    payload = {
        "items": [
            {
                "id": {"videoId": "abc123"},
                "snippet": {
                    "title": "La sicilienne",
                    "channelTitle": "Chess FR",
                    "thumbnails": {"medium": {"url": "https://img/abc123.jpg"}},
                    "publishedAt": "2026-01-15T10:00:00Z",
                },
            },
            {"id": {}, "snippet": {"title": "Entrée sans identifiant"}},
        ]
    }

    videos = YouTubeService._parse(payload)

    assert len(videos) == 1
    assert videos[0].video_id == "abc123"
    assert videos[0].url == "https://www.youtube.com/watch?v=abc123"
    assert videos[0].embed_url == "https://www.youtube.com/embed/abc123"


def test_wikichess_articles_are_chunked_by_paragraph(tmp_path):
    """Le corpus est découpé en passages, le titre venant de l'en-tête markdown."""
    from app.scripts.ingest import load_chunks

    (tmp_path / "sicilienne.md").write_text(
        "# Défense sicilienne\n\nPremier paragraphe.\n\nSecond\nparagraphe.\n",
        encoding="utf-8",
    )

    chunks = load_chunks(tmp_path)

    assert len(chunks) == 2
    assert all(chunk["title"] == "Défense sicilienne" for chunk in chunks)
    # Les retours à la ligne internes sont normalisés en espaces simples.
    assert chunks[1]["text"] == "Second paragraphe."
