"""Fixtures partagées par les tests.

Les tests s'exécutent sans aucun service externe : Lichess, Stockfish, Milvus,
YouTube et MongoDB sont remplacés par des doublures qui comptent les appels
reçus. Cela permet de vérifier le comportement de l'agent (aiguillage, cache,
dégradation gracieuse) sans dépendre du réseau.
"""

import pytest

from app.schemas.chess import EvaluationResponse, MovesResponse, TheoreticalMove
from app.schemas.video import VideoResult
from app.services.mongo import MongoError

START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


class FakeMongoRepository:
    """Doublure du dépôt MongoDB conservant les données en mémoire.

    ``available`` permet de simuler une base indisponible afin de vérifier la
    dégradation gracieuse de l'agent.
    """

    def __init__(self, available: bool = True) -> None:
        self.available = available
        self.cache: dict[str, object] = {}
        self.analyses: list[dict] = []

    def _check(self) -> None:
        if not self.available:
            raise MongoError("MongoDB is unavailable")

    async def get_cached(self, key: str):
        self._check()
        return self.cache.get(key)

    async def set_cached(self, key: str, payload) -> None:
        self._check()
        self.cache[key] = payload

    async def save_analysis(self, document: dict) -> None:
        self._check()
        self.analyses.append(document)


class FakeLichessService:
    """Doublure de l'explorateur Lichess comptant le nombre d'appels réseau.

    ``opening`` et ``has_moves`` sont indépendants : Lichess renvoie bien des
    coups sans nommer d'ouverture sur la position de départ, où aucun coup n'a
    encore été joué.
    """

    def __init__(
        self, opening: str | None = "Sicilian Defense", has_moves: bool = True
    ) -> None:
        self.opening = opening
        self.has_moves = has_moves
        self.calls = 0

    async def get_theoretical_moves(self, fen: str) -> MovesResponse:
        self.calls += 1
        move = TheoreticalMove(
            uci="e2e4", san="e4", white=10, draws=5, black=5, total=20
        )
        moves = [move] if self.has_moves else []
        return MovesResponse(fen=fen, opening=self.opening, moves=moves)


class FakeYouTubeService:
    """Doublure de l'API YouTube comptant le nombre d'appels réseau."""

    def __init__(self) -> None:
        self.calls = 0

    def build_query(self, opening: str) -> str:
        return f"{opening} chess opening tutorial"

    def search(self, opening: str) -> list[VideoResult]:
        self.calls += 1
        return [
            VideoResult(
                video_id="abc123",
                title=f"{opening} expliquée",
                channel="Chess FR",
                url="https://www.youtube.com/watch?v=abc123",
                embed_url="https://www.youtube.com/embed/abc123",
            )
        ]


@pytest.fixture
def fake_mongo() -> FakeMongoRepository:
    """Dépôt MongoDB en mémoire, disponible par défaut."""
    return FakeMongoRepository()


@pytest.fixture
def fake_lichess() -> FakeLichessService:
    """Explorateur Lichess simulé renvoyant une ouverture connue."""
    return FakeLichessService()


@pytest.fixture
def fake_youtube() -> FakeYouTubeService:
    """API YouTube simulée renvoyant une vidéo."""
    return FakeYouTubeService()


@pytest.fixture
def agent_env(monkeypatch, fake_mongo, fake_lichess, fake_youtube):
    """Branche l'agent sur des doublures pour toutes ses sources externes.

    Returns:
        Les doublures utilisées, afin que les tests puissent inspecter les
        appels reçus et le contenu de MongoDB.
    """
    from app.graph import agent_graph as agent_module
    from app.graph import cache as cache_module

    monkeypatch.setattr(cache_module, "mongo_repository", fake_mongo)
    monkeypatch.setattr(agent_module, "mongo_repository", fake_mongo)
    monkeypatch.setattr(agent_module, "lichess_service", fake_lichess)
    monkeypatch.setattr(agent_module, "youtube_service", fake_youtube)

    def fake_evaluate(fen: str) -> EvaluationResponse:
        return EvaluationResponse(fen=fen, type="cp", value=25, best_move="e2e4")

    monkeypatch.setattr(agent_module.stockfish_service, "evaluate", fake_evaluate)
    monkeypatch.setattr(
        agent_module.embedding_service, "embed_query", lambda text: [0.1, 0.2, 0.3]
    )
    monkeypatch.setattr(
        agent_module.milvus_repository,
        "search",
        lambda vector, top_k: [
            {"title": "Sicilienne", "text": "La défense sicilienne...", "score": 0.9}
        ],
    )

    return {
        "mongo": fake_mongo,
        "lichess": fake_lichess,
        "youtube": fake_youtube,
    }
