"""Client de l'API YouTube Data v3.

Encapsule les appels à l'API YouTube pour rechercher des vidéos explicatives
pertinentes sur une ouverture. Construit une requête ciblée (nom de l'ouverture +
mots-clés), transforme la réponse en modèles de l'application et gère l'absence
de clé ainsi que les erreurs de quota.
"""

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.core.config import settings
from app.schemas.video import VideoResult


class YouTubeError(Exception):
    """Levée lorsque l'API YouTube est mal configurée ou renvoie une erreur."""


class YouTubeService:
    """Client de recherche de vidéos via l'API YouTube Data v3."""

    def __init__(
        self,
        api_key: str | None = None,
        max_results: int | None = None,
        keywords: str | None = None,
    ) -> None:
        """Initialise le client.

        Args:
            api_key: Clé API YouTube (par défaut celle de la configuration).
            max_results: Nombre maximal de vidéos (par défaut celui de la config).
            keywords: Mots-clés ajoutés à la requête (par défaut ceux de la config).
        """
        self._api_key = api_key if api_key is not None else settings.youtube_api_key
        self._max_results = max_results or settings.youtube_max_results
        self._keywords = (
            keywords if keywords is not None else settings.youtube_search_keywords
        )

    def build_query(self, opening: str) -> str:
        """Construit une requête ciblée en combinant l'ouverture et les mots-clés."""
        return f"{opening} {self._keywords}".strip()

    def search(self, opening: str) -> list[VideoResult]:
        """Recherche des vidéos explicatives pour une ouverture.

        Args:
            opening: Nom de l'ouverture (ex. « défense sicilienne »).

        Returns:
            La liste des vidéos pertinentes (éventuellement vide si aucune n'est
            trouvée).

        Raises:
            YouTubeError: si la clé API est absente ou si l'API échoue (quota,
                erreur réseau, etc.).
        """
        if not self._api_key:
            raise YouTubeError(
                "YouTube API key is not configured. Set YOUTUBE_API_KEY."
            )

        try:
            youtube = build(
                "youtube", "v3", developerKey=self._api_key, cache_discovery=False
            )
            response = (
                youtube.search()
                .list(
                    q=self.build_query(opening),
                    part="snippet",
                    type="video",
                    maxResults=self._max_results,
                    safeSearch="strict",
                )
                .execute()
            )
        except HttpError as exc:
            raise YouTubeError(f"YouTube API error: {exc}") from exc

        return self._parse(response)

    @staticmethod
    def _parse(response: dict) -> list[VideoResult]:
        """Transforme la réponse de l'API YouTube en liste de ``VideoResult``."""
        videos: list[VideoResult] = []
        for item in response.get("items", []):
            video_id = item.get("id", {}).get("videoId")
            if not video_id:
                continue
            snippet = item.get("snippet", {})
            thumbnail = snippet.get("thumbnails", {}).get("medium", {}).get("url")
            videos.append(
                VideoResult(
                    video_id=video_id,
                    title=snippet.get("title", ""),
                    channel=snippet.get("channelTitle", ""),
                    url=f"https://www.youtube.com/watch?v={video_id}",
                    embed_url=f"https://www.youtube.com/embed/{video_id}",
                    thumbnail=thumbnail,
                    published_at=snippet.get("publishedAt"),
                )
            )
        return videos


youtube_service = YouTubeService()
