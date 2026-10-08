from datetime import datetime

from pydantic import HttpUrl

from app.models.anime import Anime, AnimeStatus, AnimeType
from app.schemas.common import ApiModel


class AnimeResponse(ApiModel):
    id: str
    provider: str
    provider_id: str
    title: str
    original_title: str | None
    alternative_titles: list[str]
    description: str | None
    poster_url: HttpUrl | None
    backdrop_url: HttpUrl | None
    year: int | None
    status: AnimeStatus
    type: AnimeType
    genres: list[str]
    rating: float | None
    episode_count: int | None
    current_episode: int | None
    age_rating: str | None
    voiceovers: list[str]
    updated_at: datetime | None

    @classmethod
    def from_domain(cls, anime: Anime) -> "AnimeResponse":
        return cls.model_validate(anime.model_dump())
