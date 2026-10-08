from app.core.exceptions import NotFound, ParsingError
from app.models.anime import Anime
from app.providers.base import AnimeProvider


class CatalogService:
    def __init__(self, provider: AnimeProvider) -> None:
        self.provider = provider

    async def get_anime(self, anime_id: str) -> Anime:
        if anime_id.partition(":")[0] != self.provider.key:
            raise NotFound("Unknown catalog provider namespace")
        anime = await self.provider.get_anime(anime_id)
        if anime.id != anime_id:
            raise ParsingError("Provider returned a different anime identity")
        return anime
