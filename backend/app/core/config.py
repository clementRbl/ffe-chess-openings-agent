from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "FFE Chess Openings Agent"
    api_v1_prefix: str = "/api/v1"
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    # Lichess opening explorer (reference/master games).
    # Since 2025 the explorer requires an authenticated request: provide a free
    # Lichess personal API token (https://lichess.org/account/oauth/token).
    lichess_explorer_url: str = "https://explorer.lichess.ovh/masters"
    lichess_timeout_seconds: float = 10.0
    lichess_token: str = ""

    # Stockfish engine.
    stockfish_path: str = "/usr/games/stockfish"
    stockfish_depth: int = 15
    stockfish_threads: int = 1
    stockfish_hash_mb: int = 64


settings = Settings()
