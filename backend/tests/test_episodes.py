import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.models.catalog import Page, Pagination
from app.models.episode import Episode
from app.providers.base import CatalogOperation, ProviderCapabilities
from tests.test_providers import FakeCatalog


class EpisodeCatalog(FakeCatalog):
    capabilities = ProviderCapabilities(operations=frozenset({CatalogOperation.EPISODES}))

    def __init__(self, fault: str | None = None) -> None:
        self.calls: list[tuple[str, int, int, int | None]] = []
        self.fault = fault

    async def get_episodes(
        self, anime_id: str, pagination: Pagination, *, season: int | None = None
    ) -> Page[Episode]:
        self.calls.append((anime_id, pagination.page, pagination.page_size, season))
        episode = Episode(
            id=f"fixture:{anime_id.split(':')[1]}-s{season}-e1",
            anime_id="fixture:wrong" if self.fault == "anime" else anime_id,
            season=None if self.fault == "season" else season,
            number=1,
        )
        items = [episode, episode] if self.fault == "duplicate" else [episode]
        return Page[Episode](
            items=items,
            page=pagination.page,
            page_size=pagination.page_size,
            total=len(items),
            has_next=False,
        )


def test_replaceable_provider_seasons_and_cache_parameter_isolation() -> None:
    provider = EpisodeCatalog()
    with TestClient(create_app(anime_provider=provider)) as client:
        path = "/anime/fixture:anime-1/episodes?season=2&pageSize=1"
        first = client.get(path)
        assert first.status_code == 200
        assert first.json()["items"][0]["season"] == 2
        assert first.json() == client.get(path).json()
        assert len(provider.calls) == 1
        assert client.get(path.replace("season=2", "season=3")).status_code == 200
        assert client.get(path.replace("pageSize=1", "pageSize=2")).status_code == 200
        assert client.get(path + "&page=2").status_code == 200
        assert client.get(path.replace("anime-1", "anime-2")).status_code == 200
        assert len(set(provider.calls)) == 5


@pytest.mark.parametrize("fault", ["anime", "season", "duplicate"])
def test_service_rejects_inconsistent_provider_results(fault: str) -> None:
    with TestClient(create_app(anime_provider=EpisodeCatalog(fault))) as client:
        response = client.get("/anime/fixture:anime-1/episodes?season=2")
        assert response.status_code == 502
        assert response.json()["error"]["code"] == "PARSING_ERROR"


def test_operation_capability_and_missing_provider() -> None:
    with TestClient(create_app(anime_provider=FakeCatalog())) as client:
        response = client.get("/anime/fixture:anime-1/episodes")
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "UNSUPPORTED_OPERATION"
