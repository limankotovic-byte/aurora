from datetime import date

from pydantic import Field

from app.models.anime import Anime, AnimeStatus, AnimeType
from app.models.base import DomainModel, NonEmptyString, UtcDatetime
from app.models.episode import Episode
from app.models.release import Release


class Pagination(DomainModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=50)


class Page[T](Pagination):
    items: list[T]
    has_next: bool
    total: int | None = Field(default=None, ge=0)


class SearchQuery(Pagination):
    q: NonEmptyString = Field(max_length=200)
    genre: NonEmptyString | None = None
    year: int | None = Field(default=None, ge=1, le=9999)
    type: AnimeType | None = None
    status: AnimeStatus | None = None
    rating: float | None = Field(default=None, ge=0, le=10)
    voiceover: NonEmptyString | None = None
    sort: NonEmptyString | None = None


class HomeCatalog(DomainModel):
    """Catalog sections only; personal continue-watching is an API/local concern."""

    featured: list[Anime] = Field(default_factory=list[Anime])
    new_releases: list[Anime] = Field(default_factory=list[Anime])
    latest: list[Release] = Field(default_factory=list[Release])
    ongoing: list[Anime] = Field(default_factory=list[Anime])
    popular: list[Anime] = Field(default_factory=list[Anime])
    movies: list[Anime] = Field(default_factory=list[Anime])
    donghua: list[Anime] = Field(default_factory=list[Anime])
    recently_updated: list[Anime] = Field(default_factory=list[Anime])
    upcoming: list[Anime] = Field(default_factory=list[Anime])


class ScheduleEntry(DomainModel):
    """Provisional: preserve date-only precision without inventing a timestamp."""

    anime: Anime
    episode: Episode | None = None
    expected_date: date | None = None
    expected_at: UtcDatetime | None = None
