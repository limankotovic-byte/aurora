import json
from datetime import date

from app.models.anime import Anime
from app.models.catalog import HomeCatalog, Page, Pagination, ScheduleEntry, SearchQuery
from app.models.episode import Episode
from app.models.release import Release
from app.providers.base import AnimeProvider, ProviderCapabilities
from app.services.cache import CacheService


class CachedAnimeProvider:
    def __init__(self, provider: AnimeProvider, cache: CacheService) -> None:
        self.provider = provider
        self.cache = cache

    @property
    def key(self) -> str:
        return self.provider.key

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self.provider.capabilities

    def cache_key(self, operation: str, parameters: object = None) -> str:
        return json.dumps(
            ["v1", self.key, operation, parameters], sort_keys=True, ensure_ascii=False
        )

    async def get_home(self) -> HomeCatalog:
        return await self.cache.get(self.cache_key("home"), self.provider.get_home, 600)

    async def get_anime(self, anime_id: str) -> Anime:
        return await self.cache.get(
            self.cache_key("anime", anime_id), lambda: self.provider.get_anime(anime_id), 10800
        )

    async def search(self, query: SearchQuery) -> Page[Anime]:
        return await self.cache.get(
            self.cache_key("search", query.model_dump(mode="json")),
            lambda: self.provider.search(query),
            60,
        )

    async def get_latest_releases(self, pagination: Pagination) -> Page[Release]:
        return await self.cache.get(
            self.cache_key("releases", pagination.model_dump(mode="json")),
            lambda: self.provider.get_latest_releases(pagination),
            180,
        )

    async def get_episodes(
        self, anime_id: str, pagination: Pagination, *, season: int | None = None
    ) -> Page[Episode]:
        return await self.cache.get(
            self.cache_key("episodes", [anime_id, pagination.model_dump(mode="json"), season]),
            lambda: self.provider.get_episodes(anime_id, pagination, season=season),
            180,
        )

    async def get_schedule(self, start: date, end: date) -> list[ScheduleEntry]:
        return await self.provider.get_schedule(start, end)
