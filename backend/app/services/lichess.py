import httpx

from app.core.config import settings
from app.schemas.chess import MovesResponse, TheoreticalMove


class LichessError(Exception):
    """Raised when the Lichess opening explorer cannot be reached or fails."""


class LichessService:
    """Client for the Lichess opening explorer (reference/master games)."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float | None = None,
        token: str | None = None,
    ) -> None:
        self._base_url = base_url or settings.lichess_explorer_url
        self._timeout = timeout or settings.lichess_timeout_seconds
        self._token = token if token is not None else settings.lichess_token

    def _headers(self) -> dict[str, str]:
        headers = {"User-Agent": "ffe-chess-openings-agent"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    async def get_theoretical_moves(self, fen: str) -> MovesResponse:
        """Return the theoretical moves known for a position from Lichess.

        Raises:
            LichessError: on timeout, network error or unexpected response.
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
        moves = [
            TheoreticalMove(
                uci=move["uci"],
                san=move["san"],
                white=move.get("white", 0),
                draws=move.get("draws", 0),
                black=move.get("black", 0),
                total=move.get("white", 0) + move.get("draws", 0) + move.get("black", 0),
            )
            for move in data.get("moves", [])
        ]
        opening = data.get("opening")
        opening_name = opening["name"] if opening else None
        return MovesResponse(fen=fen, opening=opening_name, moves=moves)


lichess_service = LichessService()
