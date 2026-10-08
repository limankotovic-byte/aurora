from enum import StrEnum
from typing import Self

from pydantic import Field, HttpUrl, model_validator

from app.models.base import DomainModel, EntityId, NonEmptyString, ProviderKey, UtcDatetime


class AnimeStatus(StrEnum):
    UNKNOWN = "UNKNOWN"
    UPCOMING = "UPCOMING"
    ONGOING = "ONGOING"
    COMPLETED = "COMPLETED"


class AnimeType(StrEnum):
    UNKNOWN = "UNKNOWN"
    TV = "TV"
    MOVIE = "MOVIE"
    OVA = "OVA"
    ONA = "ONA"
    SPECIAL = "SPECIAL"


class Anime(DomainModel):
    id: EntityId
    provider: ProviderKey
    provider_id: NonEmptyString
    title: NonEmptyString
    original_title: NonEmptyString | None = None
    alternative_titles: list[NonEmptyString] = Field(default_factory=list)
    description: str | None = None
    poster_url: HttpUrl | None = None
    backdrop_url: HttpUrl | None = None
    year: int | None = Field(default=None, ge=1, le=9999)
    status: AnimeStatus = AnimeStatus.UNKNOWN
    type: AnimeType = AnimeType.UNKNOWN
    genres: list[NonEmptyString] = Field(default_factory=list)
    rating: float | None = Field(default=None, ge=0, le=10)
    episode_count: int | None = Field(default=None, ge=0)
    current_episode: int | None = Field(default=None, ge=0)
    age_rating: NonEmptyString | None = None
    voiceovers: list[NonEmptyString] = Field(default_factory=list)
    updated_at: UtcDatetime | None = None

    @model_validator(mode="after")
    def validate_provider_namespace(self) -> Self:
        if self.id.partition(":")[0] != self.provider:
            raise ValueError("Anime ID namespace must match its provider")
        return self
