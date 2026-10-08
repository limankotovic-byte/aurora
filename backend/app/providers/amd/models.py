from pydantic import Field, HttpUrl

from app.models.base import DomainModel, NonEmptyString


class ParsedAnimeDetails(DomainModel):
    """Five-field parser result, not a fabricated complete Anime or HTTP DTO."""

    title: NonEmptyString
    poster_url: HttpUrl | None = None
    description: NonEmptyString | None = None
    genres: list[NonEmptyString] = Field(default_factory=list[NonEmptyString])
    year: int | None = Field(default=None, ge=1, le=9999)
