"""Schémas Pydantic des réponses de la recherche de vidéos YouTube.

Ces modèles définissent la structure des vidéos explicatives renvoyées par la
route ``/videos/{opening}`` (métadonnées, lien de visionnage et lien
d'intégration pour le streaming).
"""

from pydantic import BaseModel, Field


class VideoResult(BaseModel):
    """Une vidéo YouTube pertinente pour une ouverture."""

    video_id: str = Field(description="Identifiant YouTube de la vidéo.")
    title: str = Field(description="Titre de la vidéo.")
    channel: str = Field(description="Nom de la chaîne YouTube.")
    url: str = Field(description="Lien de visionnage de la vidéo.")
    embed_url: str = Field(description="Lien d'intégration (streaming) de la vidéo.")
    thumbnail: str | None = Field(default=None, description="URL de la miniature.")
    published_at: str | None = Field(
        default=None, description="Date de publication (ISO 8601)."
    )


class VideosResponse(BaseModel):
    """Vidéos explicatives récupérées pour une ouverture donnée."""

    opening: str
    videos: list[VideoResult] = Field(default_factory=list)
