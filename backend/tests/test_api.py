"""Tests des routes de l'API (contrat HTTP, sans service externe)."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import START_FEN

client = TestClient(app)


def test_healthcheck_reports_the_service_as_available():
    """La sonde de santé répond ``ok`` (utilisée par Docker)."""
    response = client.get("/api/v1/healthcheck")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.parametrize("route", ["/api/v1/moves", "/api/v1/evaluate"])
def test_invalid_fen_is_rejected_before_calling_external_services(route):
    """Une FEN invalide renvoie 400 sans solliciter Lichess ni Stockfish."""
    response = client.get(f"{route}/pas-une-position")

    assert response.status_code == 400
    assert "Invalid FEN" in response.json()["detail"]


def test_analyze_rejects_an_invalid_fen():
    """La route de l'agent valide elle aussi la position avant de travailler."""
    response = client.get("/api/v1/analyze", params={"fen": "pas-une-position"})

    assert response.status_code == 400


def test_vector_search_requires_a_query():
    """La recherche vectorielle exige une requête d'au moins deux caractères."""
    assert client.get("/api/v1/vector-search").status_code == 422
    assert client.get("/api/v1/vector-search", params={"query": "a"}).status_code == 422


def test_analyze_returns_the_full_recommendation(agent_env):
    """L'analyse complète renvoie toutes les sources agrégées par l'agent."""
    response = client.get("/api/v1/analyze", params={"fen": START_FEN})

    assert response.status_code == 200
    body = response.json()
    assert body["fen"] == START_FEN
    assert body["opening"] == "Sicilian Defense"
    assert body["in_theory"] is True
    assert body["theoretical_moves"][0]["san"] == "e4"
    assert body["evaluation"]["best_move"] == "e2e4"
    assert body["videos"][0]["video_id"] == "abc123"
    assert body["sources"]["lichess"]["ok"] is True
