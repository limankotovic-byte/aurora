from app.core.exceptions import UnsupportedOperation
from app.models.anime import Anime
from app.models.catalog import Page, SearchQuery
from app.providers.base import AnimeProvider, CatalogOperation

FILTER_FIELDS = ("genre", "year", "type", "status", "rating", "voiceover", "sort")


def check_filters(query: SearchQuery, supported: frozenset[str]) -> None:
    if any(getattr(query, field) is not None and field not in supported for field in FILTER_FIELDS):
        raise UnsupportedOperation("Unsupported search filter")


class SearchService:
    def __init__(self, provider: AnimeProvider) -> None:
        self.provider = provider

    async def search(self, query: SearchQuery) -> Page[Anime]:
        if CatalogOperation.SEARCH not in self.provider.capabilities.operations:
            raise UnsupportedOperation()
        check_filters(query, self.provider.capabilities.search_filters)
        return await self.provider.search(query)
