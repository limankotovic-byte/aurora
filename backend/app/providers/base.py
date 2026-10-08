from datetime import date
from enum import StrEnum
from typing import Protocol

from pydantic import Field, HttpUrl

from app.models.anime import Anime
from app.models.base import DomainModel, ProviderKey
from app.models.catalog import HomeCatalog, Page, Pagination, ScheduleEntry, SearchQuery
from app.models.episode import Episode
from app.models.player import PlayerInfo
from app.models.release import Release


class CatalogOperation(StrEnum):
    HOME = "HOME"
    SEARCH = "SEARCH"
    ANIME = "ANIME"
    EPISODES = "EPISODES"
    RELEASES = "RELEASES"
    SCHEDULE = "SCHEDULE"


class ProviderCapabilities(DomainModel):
    operations: frozenset[CatalogOperation] = Field(default_factory=frozenset[CatalogOperation])
    search_filters: frozenset[str] = Field(default_factory=frozenset[str])


class AnimeProvider(Protocol):
    """IDs passed to these methods are normalized IDs, not URLs or raw HTML keys.

    Implementations raise typed AppError failures; unsupported operations raise
    UnsupportedOperation. Empty results mean a successful empty catalog only.
    """

    @property
    def key(self) -> ProviderKey: ...

    @property
    def capabilities(self) -> ProviderCapabilities: ...

    async def get_home(self) -> HomeCatalog: ...

    async def search(self, query: SearchQuery) -> Page[Anime]: ...

    async def get_anime(self, anime_id: str) -> Anime: ...

    async def get_episodes(
        self, anime_id: str, pagination: Pagination, *, season: int | None = None
    ) -> Page[Episode]: ...

    async def get_latest_releases(self, pagination: Pagination) -> Page[Release]: ...

    async def get_schedule(self, start: date, end: date) -> list[ScheduleEntry]: ...


class PlayerProvider(Protocol):
    """Independent contract for public/authorized playback only.

    supports_embed means a supported source embed was resolved, not that media
    playback succeeded. get_embed_url returns None only for PlayerUnavailable;
    validation, not-found, network and parsing errors remain typed failures.
    """

    @property
    def key(self) -> ProviderKey: ...

    async def get_player(self, episode_id: str) -> PlayerInfo: ...

    async def supports_embed(self, episode_id: str) -> bool: ...

    async def get_embed_url(self, episode_id: str) -> HttpUrl | None: ...
