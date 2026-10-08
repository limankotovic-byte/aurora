from datetime import date

from pydantic import Field, HttpUrl

from app.models.base import DomainModel, EntityId, NonEmptyString


class Episode(DomainModel):
    id: EntityId
    anime_id: EntityId
    season: int | None = Field(default=None, ge=0)
    number: float | None = Field(default=None, ge=0)
    title: NonEmptyString | None = None
    release_date: date | None = None
    thumbnail: HttpUrl | None = None
    available: bool = False
    player_id: NonEmptyString | None = None
