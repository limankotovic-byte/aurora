from datetime import date
from typing import Annotated

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from pydantic import HttpUrl

from app.api.dependencies import get_anime_provider, get_player_provider
from app.core.config import Settings
from app.core.exceptions import NotFound, UnsupportedOperation
from app.main import create_app
from app.models.anime import Anime
from app.models.catalog import HomeCatalog, Page, Pagination, ScheduleEntry, SearchQuery
from app.models.episode import Episode
from app.models.player import PlayerInfo, WebEmbedPlayerInfo
from app.models.release import Release
from app.providers.base import (
    AnimeProvider,
    CatalogOperation,
    PlayerProvider,
    ProviderCapabilities,
)


class FakeCatalog:
    key = "fixture"
    capabilities = ProviderCapabilities(operations=frozenset({CatalogOperation.ANIME}))

    async def get_anime(self, anime_id: str) -> Anime:
        if anime_id != "fixture:anime-1":
            raise NotFound()
        return Anime(id=anime_id, provider=self.key, provider_id="1", title="Fixture Anime")

    async def get_home(self) -> HomeCatalog:
        raise UnsupportedOperation()

    async def search(self, query: SearchQuery) -> Page[Anime]:
        raise UnsupportedOperation()

    async def get_episodes(
        self, anime_id: str, pagination: Pagination, *, season: int | None = None
    ) -> Page[Episode]:
        raise UnsupportedOperation()

    async def get_latest_releases(self, pagination: Pagination) -> Page[Release]:
        raise UnsupportedOperation()

    async def get_schedule(self, start: date, end: date) -> list[ScheduleEntry]:
        raise UnsupportedOperation()


class FakePlayer:
    key = "public-player"

    async def get_player(self, episode_id: str) -> PlayerInfo:
        return WebEmbedPlayerInfo(provider=self.key, embed_url=await self.get_embed_url(episode_id))

    async def supports_embed(self, episode_id: str) -> bool:
        return True

    async def get_embed_url(self, episode_id: str) -> HttpUrl:
        return HttpUrl("https://player.example/public")


def mount_probe_routes(app: FastAPI) -> None:
    # Test-only routes exercise DI; they are never registered by create_app.
    @app.get("/probe/catalog/{anime_id}")
    async def catalog_probe(
        anime_id: str, provider: Annotated[AnimeProvider, Depends(get_anime_provider)]
    ) -> dict[str, str]:
        anime = await provider.get_anime(anime_id)
        return {"id": anime.id, "title": anime.title}

    @app.get("/probe/unsupported")
    async def unsupported_probe(
        provider: Annotated[AnimeProvider, Depends(get_anime_provider)],
    ) -> dict[str, str]:
        await provider.get_home()
        return {"status": "unexpected"}

    @app.get("/probe/player")
    async def player_probe(
        provider: Annotated[PlayerProvider, Depends(get_player_provider)],
    ) -> dict[str, str]:
        info = await provider.get_player("fixture:episode-1")
        return {"provider": info.provider, "type": info.type}


def test_catalog_and_player_are_independently_injected() -> None:
    app = create_app(
        Settings(environment="test"), anime_provider=FakeCatalog(), player_provider=FakePlayer()
    )
    mount_probe_routes(app)
    with TestClient(app) as client:
        assert client.get("/probe/catalog/fixture:anime-1").json()["title"] == "Fixture Anime"
        assert client.get("/probe/catalog/fixture:missing").status_code == 404
        assert client.get("/probe/unsupported").json()["error"]["code"] == "UNSUPPORTED_OPERATION"
        assert client.get("/probe/player").json() == {
            "provider": "public-player",
            "type": "WEB_EMBED",
        }


def test_catalog_dependency_can_be_overridden_without_player(app: FastAPI) -> None:
    mount_probe_routes(app)
    app.dependency_overrides[get_anime_provider] = lambda: FakeCatalog()
    with TestClient(app) as client:
        assert client.get("/probe/catalog/fixture:anime-1").status_code == 200
        assert client.get("/probe/player").json()["error"]["code"] == "PLAYER_UNAVAILABLE"


@pytest.mark.parametrize(
    ("path", "code"),
    [
        ("/probe/catalog/fixture:anime-1", "PROVIDER_UNAVAILABLE"),
        ("/probe/player", "PLAYER_UNAVAILABLE"),
    ],
)
def test_missing_provider_does_not_break_health(app: FastAPI, path: str, code: str) -> None:
    mount_probe_routes(app)
    with TestClient(app) as client:
        response = client.get(path)
        assert response.status_code == 503
        assert response.json()["error"]["code"] == code
        assert client.get("/health").status_code == 200
