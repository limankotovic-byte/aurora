import asyncio
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.exceptions import ParsingError
from app.main import create_app
from app.models.catalog import Pagination, SearchQuery
from app.providers.amd.home import parse_home, parse_releases
from app.providers.amd.provider import AmdProvider
from app.services.cache import CacheService
from app.services.cached_provider import CachedAnimeProvider

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
HOME = (FIXTURES / "amd_home.html").read_bytes()
ONGOING = (FIXTURES / "amd_ongoing.html").read_bytes()
POPULAR = (FIXTURES / "amd_popular.html").read_bytes()


def test_real_home_sections_and_release_identity() -> None:
    result = parse_home(HOME, ONGOING, POPULAR)
    assert len(result.featured) == 14
    assert len(result.new_releases) == 12
    assert len(result.ongoing) == 12 and len(result.popular) == 20
    assert all(item.status == "ONGOING" for item in result.ongoing)
    assert result.popular[0].id == "amd:1200"
    release = result.latest[0]
    assert release.anime.id == "amd:5781"
    assert release.episode.id == "amd:5781-episode-1"
    assert release.episode.number == 1 and release.episode.season is None
    assert release.released_at is None and release.episode.player_id is None
    assert release.episode.available is False


@pytest.mark.parametrize("field", ["owl-carou", "amd-poslednie-serii", "new_anime"])
def test_missing_section_is_error_not_empty_home(field: str) -> None:
    with pytest.raises(ParsingError):
        parse_home(HOME.replace(field.encode(), b"changed"), ONGOING, POPULAR)


def test_invalid_episode_does_not_create_fabricated_release() -> None:
    with pytest.raises(ParsingError):
        parse_releases(HOME.replace(b"<span>1</span>", b"<span>unknown</span>"))


def test_home_and_release_endpoints_cache_and_serialize() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        body = {"/": HOME, "/ongoingi/": ONGOING, "/top-100-1.html": POPULAR}[request.url.path]
        return httpx.Response(200, content=body, headers={"content-type": "text/html"})

    upstream = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        with TestClient(create_app(anime_provider=AmdProvider(upstream))) as client:
            first = client.get("/home")
            assert first.status_code == 200, first.text
            assert first.json() == client.get("/home").json()
            assert len(calls) == 3
            home = first.json()
            assert home["continueWatching"] == []
            assert len(home["newReleases"]) == 12
            assert home["latest"][0]["episode"]["animeId"] == "amd:5781"
            response = client.get("/releases/latest", params={"pageSize": 3, "page": 2})
            assert response.status_code == 200, response.text
            feed = response.json()
            assert feed["scope"] == "RECENT_WINDOW" and feed["total"] == 10
            assert len(feed["items"]) == 3 and feed["hasNext"]
            assert client.get("/releases/latest", params={"pageSize": 3, "page": 2}).json() == feed
            assert len(calls) == 4
            assert client.get("/releases/latest?page=0").status_code == 422
            assert len(calls) == 4
            assert client.get("/releases/latest?page=20").json()["items"] == []
    finally:
        asyncio.run(upstream.aclose())


def test_upstream_failure_not_cached_as_success() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(503)
        return httpx.Response(200, content=HOME, headers={"content-type": "text/html"})

    upstream = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        with TestClient(create_app(anime_provider=AmdProvider(upstream))) as client:
            assert client.get("/releases/latest").status_code == 503
            assert client.get("/releases/latest").status_code == 200
        assert calls == 2
    finally:
        asyncio.run(upstream.aclose())


def test_cache_keys_isolate_provider_operation_filters_and_pagination() -> None:
    upstream = httpx.AsyncClient()
    try:
        underlying = AmdProvider(upstream)
        provider = CachedAnimeProvider(underlying, CacheService())
        keys = {
            provider.cache_key("home"),
            provider.cache_key("search", SearchQuery(q="мир").model_dump(mode="json")),
            provider.cache_key("search", SearchQuery(q="мир", page=2).model_dump(mode="json")),
            provider.cache_key("search", SearchQuery(q="мир", year=2023).model_dump(mode="json")),
            provider.cache_key("releases", Pagination().model_dump(mode="json")),
        }
        assert len(keys) == 5
        assert provider.cache_key("test", {"b": 2, "a": 1}) == provider.cache_key(
            "test", {"a": 1, "b": 2}
        )
        original = provider.cache_key("home")
        underlying.key = "other"
        assert provider.cache_key("home") != original
    finally:
        asyncio.run(upstream.aclose())
