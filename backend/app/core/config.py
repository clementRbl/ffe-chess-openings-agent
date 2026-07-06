"""Configuration centralisée de l'application.

Toutes les valeurs sont chargées depuis les variables d'environnement (ou le
fichier ``.env``) via ``pydantic-settings``, ce qui permet de configurer
l'application sans modifier le code (ports, hôtes des services, modèle
d'embedding, etc.).
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Paramètres de l'application chargés depuis l'environnement.

    Chaque attribut peut être surchargé par une variable d'environnement du même
    nom (en majuscules). Les valeurs par défaut correspondent à un fonctionnement
    au sein du réseau Docker Compose.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "FFE Chess Openings Agent"
    api_v1_prefix: str = "/api/v1"
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    # Explorateur d'ouvertures Lichess (parties de maîtres / références).
    # Depuis 2025, l'explorateur exige une requête authentifiée : fournir un
    # token personnel Lichess gratuit (https://lichess.org/account/oauth/token).
    lichess_explorer_url: str = "https://explorer.lichess.ovh/masters"
    lichess_timeout_seconds: float = 10.0
    lichess_token: str = ""

    # Moteur d'échecs Stockfish.
    stockfish_path: str = "/usr/games/stockfish"
    stockfish_depth: int = 15
    stockfish_threads: int = 1
    stockfish_hash_mb: int = 64

    # Base de données vectorielle Milvus.
    milvus_host: str = "localhost"
    milvus_port: int = 19530
    milvus_collection: str = "wikichess_openings"

    # Embeddings (sentence-transformers).
    embedding_model: str = "Qwen/Qwen3-Embedding-0.6B"
    embedding_dim: int = 1024
    vector_search_top_k: int = 3

    # Emplacement du corpus (à l'intérieur du conteneur).
    wikichess_data_dir: str = "data/wikichess"

    @property
    def milvus_uri(self) -> str:
        """URI de connexion à Milvus construite à partir de l'hôte et du port."""
        return f"http://{self.milvus_host}:{self.milvus_port}"


settings = Settings()
