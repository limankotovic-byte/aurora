from app.core.exceptions import NotFound, ParsingError, UnsupportedOperation
from app.models.catalog import Page, Pagination
from app.models.episode import Episode
from app.providers.base import AnimeProvider, CatalogOperation


class EpisodeService:
    def __init__(self, provider: AnimeProvider) -> None:
        self.provider = provider

    async def get_episodes(
        self, anime_id: str, pagination: Pagination, *, season: int | None = None
    ) -> Page[Episode]:
        if anime_id.partition(":")[0] != self.provider.key:
            raise NotFound("Unknown catalog provider namespace")
        if CatalogOperation.EPISODES not in self.provider.capabilities.operations:
            raise UnsupportedOperation()
        result = await self.provider.get_episodes(anime_id, pagination, season=season)
        if any(
            item.anime_id != anime_id or (season is not None and item.season != season)
            for item in result.items
        ) or len({item.id for item in result.items}) != len(result.items):
            raise ParsingError("Provider returned inconsistent episode identities or seasons")
        return result
