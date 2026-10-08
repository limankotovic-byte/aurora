from datetime import date

from pydantic import Field, HttpUrl

from app.models.catalog import Pagination
from app.models.episode import Episode
from app.schemas.common import ApiModel


class EpisodeResponse(ApiModel):
    id: str
    anime_id: str
    season: int | None
    number: float | None
    title: str | None
    release_date: date | None
    thumbnail: HttpUrl | None
    available: bool
    player_id: str | None

    @classmethod
    def from_domain(cls, episode: Episode) -> "EpisodeResponse":
        return cls.model_validate(episode.model_dump())


class EpisodeParams(Pagination, ApiModel):
    season: int | None = Field(default=None, ge=0)


class EpisodePageResponse(ApiModel):
    items: list[EpisodeResponse]
    page: int
    page_size: int
    has_next: bool
    total: int | None
