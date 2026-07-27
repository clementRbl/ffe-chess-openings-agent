"""Tests du cache MongoDB et de l'historique des analyses."""

from app.graph.agent_graph import agent_graph
from app.graph.cache import cache_get, cache_set
from tests.conftest import START_FEN


async def test_cache_get_returns_stored_value(monkeypatch, fake_mongo):
    """Une valeur écrite dans le cache est relue à l'identique."""
    from app.graph import cache as cache_module

    monkeypatch.setattr(cache_module, "mongo_repository", fake_mongo)

    status = await cache_set("lichess:test", {"opening": "Sicilienne"})
    value, read_status = await cache_get("lichess:test")

    assert status.ok
    assert read_status.ok
    assert value == {"opening": "Sicilienne"}


async def test_cache_reports_failure_without_raising(monkeypatch, fake_mongo):
    """Une base indisponible dégrade le cache sans lever d'exception."""
    from app.graph import cache as cache_module

    fake_mongo.available = False
    monkeypatch.setattr(cache_module, "mongo_repository", fake_mongo)

    value, read_status = await cache_get("lichess:test")
    write_status = await cache_set("lichess:test", {"opening": "Sicilienne"})

    assert value is None
    assert not read_status.ok
    assert not write_status.ok
    assert "unavailable" in read_status.detail


async def test_second_analysis_hits_the_cache(agent_env):
    """La deuxième analyse d'une même position n'appelle plus les API externes."""
    await agent_graph.ainvoke({"fen": START_FEN, "sources": {}})
    await agent_graph.ainvoke({"fen": START_FEN, "sources": {}})

    assert agent_env["lichess"].calls == 1
    assert agent_env["youtube"].calls == 1


async def test_analysis_is_saved_to_history(agent_env):
    """Chaque analyse est enregistrée dans l'historique MongoDB."""
    state = await agent_graph.ainvoke({"fen": START_FEN, "sources": {}})

    analyses = agent_env["mongo"].analyses
    assert len(analyses) == 1
    assert analyses[0]["fen"] == START_FEN
    assert analyses[0]["opening"] == "Sicilian Defense"
    assert analyses[0]["summary"] == state["summary"]


async def test_analysis_survives_mongo_outage(agent_env):
    """Une panne de MongoDB n'empêche pas l'agent de répondre."""
    agent_env["mongo"].available = False

    state = await agent_graph.ainvoke({"fen": START_FEN, "sources": {}})

    assert state["summary"]
    assert state["theoretical_moves"]
    assert not state["sources"]["mongo"].ok
    assert state["sources"]["lichess"].ok
