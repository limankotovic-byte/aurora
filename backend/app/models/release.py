from typing import Self

from pydantic import model_validator

from app.models.anime import Anime
from app.models.base import DomainModel, ProviderKey, UtcDatetime
from app.models.episode import Episode


class Release(DomainModel):
    anime: Anime
    episode: Episode
    released_at: UtcDatetime | None = None
    provider: ProviderKey

    @model_validator(mode="after")
    def validate_relationships(self) -> Self:
        if self.episode.anime_id != self.anime.id:
            raise ValueError("Release episode must belong to the referenced anime")
        if self.provider != self.anime.provider:
            raise ValueError("Release provider must match its anime provider")
        return self
