from datetime import datetime
from typing import Literal

from app.models.catalog import Pagination
from app.models.release import Release
from app.schemas.anime import AnimeResponse
from app.schemas.common import ApiModel
from app.schemas.episodes import EpisodeResponse


class ReleaseResponse(ApiModel):
    anime: AnimeResponse
    episode: EpisodeResponse
    released_at: datetime | None
    provider: str

    @classmethod
    def from_domain(cls, release: Release) -> "ReleaseResponse":
        return cls(
            anime=AnimeResponse.from_domain(release.anime),
            episode=EpisodeResponse.from_domain(release.episode),
            released_at=release.released_at,
            provider=release.provider,
        )


class ContinueWatchingResponse(ApiModel):
    anime: AnimeResponse
    episode: EpisodeResponse
    position: int | None
    duration: int | None


class HomeResponse(ApiModel):
    featured: list[AnimeResponse]
    continue_watching: list[ContinueWatchingResponse]
    latest: list[ReleaseResponse]
    new_releases: list[AnimeResponse]
    ongoing: list[AnimeResponse]
    popular: list[AnimeResponse]
    movies: list[AnimeResponse]
    donghua: list[AnimeResponse]
    recently_updated: list[AnimeResponse]
    upcoming: list[AnimeResponse]


class ReleaseParams(Pagination, ApiModel):
    pass


class ReleasePageResponse(ApiModel):
    items: list[ReleaseResponse]
    page: int
    page_size: int
    has_next: bool
    total: int | None
    scope: Literal["RECENT_WINDOW"] = "RECENT_WINDOW"
