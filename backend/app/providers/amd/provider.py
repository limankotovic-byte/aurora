import asyncio
from datetime import UTC, date, datetime

import httpx

from app.core.exceptions import UnsupportedOperation
from app.models.anime import Anime
from app.models.catalog import HomeCatalog, Page, Pagination, ScheduleEntry, SearchQuery
from app.models.episode import Episode
from app.models.release import Release
from app.providers.amd.episodes import parse_episodes
from app.providers.amd.home import HOME_URL, fetch_html, get_home, parse_releases
from app.providers.amd.identity import source_id
from app.providers.amd.pages import MAX_HTML_BYTES as MAX_HTML_BYTES
from app.providers.amd.pages import MAX_REDIRECTS as MAX_REDIRECTS
from app.providers.amd.pages import fetch_detail_html
from app.providers.amd.parser import parse_anime_page
from app.providers.amd.search import search as search_amd
from app.providers.base import CatalogOperation, ProviderCapabilities


class AmdProvider:
    key = "amd"
    capabilities = ProviderCapabilities(
        operations=frozenset(
            {
                CatalogOperation.ANIME,
                CatalogOperation.SEARCH,
                CatalogOperation.HOME,
                CatalogOperation.RELEASES,
                CatalogOperation.EPISODES,
            }
        )
    )

    def __init__(self, client: httpx.AsyncClient) -> None:
        self.client = client

    async def get_anime(self, anime_id: str) -> Anime:
        provider_id = source_id(anime_id)
        body, page_url = await self._get_detail_html(provider_id)
        details = await asyncio.to_thread(parse_anime_page, body, page_url=page_url)
        return Anime(
            id=anime_id,
            provider=self.key,
            provider_id=provider_id,
            updated_at=datetime.now(UTC),
            **details.model_dump(),
        )

    async def _get_detail_html(self, provider_id: str) -> tuple[bytes, str]:
        return await fetch_detail_html(self.client, provider_id)

    async def get_home(self) -> HomeCatalog:
        return await get_home(self.client)

    async def search(self, query: SearchQuery) -> Page[Anime]:
        return await search_amd(self.client, query)

    async def get_episodes(
        self, anime_id: str, pagination: Pagination, *, season: int | None = None
    ) -> Page[Episode]:
        provider_id = source_id(anime_id)
        if season is not None:
            raise UnsupportedOperation("AMD episode navigation has no season metadata")
        body, _ = await self._get_detail_html(provider_id)
        episodes = await asyncio.to_thread(parse_episodes, body, anime_id=anime_id)
        start = (pagination.page - 1) * pagination.page_size
        end = start + pagination.page_size
        return Page[Episode](
            items=episodes[start:end],
            page=pagination.page,
            page_size=pagination.page_size,
            total=len(episodes),
            has_next=end < len(episodes),
        )

    async def get_latest_releases(self, pagination: Pagination) -> Page[Release]:
        body = await fetch_html(self.client, HOME_URL)
        releases = await asyncio.to_thread(parse_releases, body)
        start = (pagination.page - 1) * pagination.page_size
        end = start + pagination.page_size
        return Page[Release](
            items=releases[start:end],
            page=pagination.page,
            page_size=pagination.page_size,
            total=len(releases),
            has_next=end < len(releases),
        )

    async def get_schedule(self, start: date, end: date) -> list[ScheduleEntry]:
        raise UnsupportedOperation()
