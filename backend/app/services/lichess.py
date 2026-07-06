"""Client de l'explorateur d'ouvertures Lichess.

Encapsule les appels HTTP à l'explorateur d'ouvertures Lichess (parties de
maîtres / références) et transforme la réponse en modèles de l'application. Gère
les délais d'attente, les erreurs réseau et l'authentification par token.
"""

import httpx

from app.core.config import settings
from app.schemas.chess import MovesResponse, TheoreticalMove


class LichessError(Exception):
    """Levée lorsque l'explorateur Lichess est injoignable ou renvoie une erreur."""


class LichessService:
    """Client de l'explorateur d'ouvertures Lichess (parties de référence)."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float | None = None,
        token: str | None = None,
    ) -> None:
        """Initialise le client.

        Args:
            base_url: URL de l'explorateur (par défaut celle de la configuration).
            timeout: Délai d'attente en secondes (par défaut celui de la config).
            token: Token personnel Lichess (par défaut celui de la config).
        """
        self._base_url = base_url or settings.lichess_explorer_url
        self._timeout = timeout or settings.lichess_timeout_seconds
        self._token = token if token is not None else settings.lichess_token

    def _headers(self) -> dict[str, str]:
        """Construit les en-têtes HTTP, avec le token d'authentification si présent."""
        headers = {"User-Agent": "ffe-chess-openings-agent"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    async def get_theoretical_moves(self, fen: str) -> MovesResponse:
        """Renvoie les coups théoriques connus pour une position via Lichess.

        Args:
            fen: Position au format FEN.

        Returns:
            Les coups théoriques et, le cas échéant, le nom de l'ouverture.

        Raises:
            LichessError: en cas de délai dépassé, d'erreur réseau, d'absence
                d'authentification (401) ou de réponse inattendue.
        """
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(
                    self._base_url, params={"fen": fen}, headers=self._headers()
                )
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise LichessError("Lichess request timed out") from exc
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 401:
                raise LichessError(
                    "Lichess opening explorer requires authentication. "
                    "Set a valid LICHESS_TOKEN "
                    "(https://lichess.org/account/oauth/token)."
                ) from exc
            raise LichessError(f"Lichess request failed: {exc}") from exc
        except httpx.HTTPError as exc:
            raise LichessError(f"Lichess request failed: {exc}") from exc

        return self._parse(fen, response.json())

    @staticmethod
    def _parse(fen: str, data: dict) -> MovesResponse:
        """Transforme la réponse JSON de Lichess en modèle ``MovesResponse``."""
        moves = [
            TheoreticalMove(
                uci=move["uci"],
                san=move["san"],
                white=move.get("white", 0),
                draws=move.get("draws", 0),
                black=move.get("black", 0),
                total=move.get("white", 0)
                + move.get("draws", 0)
                + move.get("black", 0),
            )
            for move in data.get("moves", [])
        ]
        opening = data.get("opening")
        opening_name = opening["name"] if opening else None
        return MovesResponse(fen=fen, opening=opening_name, moves=moves)


lichess_service = LichessService()
