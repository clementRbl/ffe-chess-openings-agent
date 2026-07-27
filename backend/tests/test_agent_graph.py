"""Tests du workflow LangGraph de l'agent.

Vérifient les deux comportements structurants attendus par la mission :
l'aiguillage vers la bonne source d'information selon que la position est dans
la théorie ou non, et la dégradation gracieuse en cas de panne d'une source.
"""

from app.graph.agent_graph import agent_graph
from tests.conftest import START_FEN


async def test_known_opening_is_enriched_with_context_and_videos(agent_env):
    """Une position théorique déclenche l'enrichissement contexte + vidéos."""
    state = await agent_graph.ainvoke({"fen": START_FEN, "sources": {}})

    assert state["in_theory"] is True
    assert state["opening"] == "Sicilian Defense"
    assert state["context"]
    assert state["videos"]
    assert "Sicilian Defense" in state["summary"]


async def test_position_in_theory_without_opening_name_is_not_enriched(agent_env):
    """Des coups théoriques sans nom d'ouverture ne déclenchent pas l'enrichissement.

    C'est le cas de la position de départ : Lichess renvoie les coups les plus
    joués mais aucune ouverture, puisqu'aucun coup n'a encore été joué. Sans nom
    à rechercher, interroger Milvus et YouTube n'aurait pas de sens.
    """
    agent_env["lichess"].opening = None

    state = await agent_graph.ainvoke({"fen": START_FEN, "sources": {}})

    assert state["in_theory"] is True
    assert "context" not in state
    assert agent_env["youtube"].calls == 0
    assert "milvus" not in state["sources"]
    assert state["sources"]["lichess"].ok
    # Le résumé ne doit pas laisser apparaître un nom d'ouverture vide.
    assert state["summary"] == (
        "Position connue de la théorie. Coups principaux recommandés : e4."
    )


async def test_unknown_position_falls_back_to_the_engine(agent_env):
    """Hors théorie, l'agent s'appuie sur Stockfish et n'appelle pas YouTube."""
    agent_env["lichess"].opening = None
    agent_env["lichess"].has_moves = False

    state = await agent_graph.ainvoke({"fen": START_FEN, "sources": {}})

    assert state["in_theory"] is False
    # Les nœuds « contexte » et « vidéos » n'ont pas été traversés : les clés
    # correspondantes restent absentes de l'état.
    assert "context" not in state
    assert "videos" not in state
    assert agent_env["youtube"].calls == 0
    # Le coup du moteur est explicité plutôt que laissé en notation UCI brute.
    assert "e2 vers e4" in state["summary"]


async def test_evaluation_is_always_present(agent_env):
    """L'évaluation moteur est produite quel que soit le chemin emprunté."""
    state = await agent_graph.ainvoke({"fen": START_FEN, "sources": {}})

    assert state["evaluation"].type == "cp"
    assert state["evaluation"].value == 25
    assert state["sources"]["stockfish"].ok


async def test_lichess_outage_does_not_break_the_analysis(agent_env, monkeypatch):
    """Une panne de Lichess laisse l'agent répondre avec les autres sources."""
    from app.graph import agent_graph as agent_module
    from app.services.lichess import LichessError

    async def failing_call(fen: str):
        raise LichessError("Lichess request timed out")

    monkeypatch.setattr(
        agent_module.lichess_service, "get_theoretical_moves", failing_call
    )

    state = await agent_graph.ainvoke({"fen": START_FEN, "sources": {}})

    assert state["summary"]
    assert state["evaluation"] is not None
    assert not state["sources"]["lichess"].ok
    assert "timed out" in state["sources"]["lichess"].detail


async def test_youtube_outage_does_not_break_the_analysis(agent_env, monkeypatch):
    """Une panne de YouTube laisse le reste de la recommandation intact."""
    from app.graph import agent_graph as agent_module
    from app.services.youtube import YouTubeError

    def failing_search(opening: str):
        raise YouTubeError("YouTube API error: quota exceeded")

    monkeypatch.setattr(agent_module.youtube_service, "search", failing_search)

    state = await agent_graph.ainvoke({"fen": START_FEN, "sources": {}})

    assert state["videos"] == []
    assert state["context"]
    assert not state["sources"]["youtube"].ok
    assert state["sources"]["lichess"].ok
