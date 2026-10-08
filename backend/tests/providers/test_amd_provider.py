import asyncio
from collections.abc import Callable
from pathlib import Path
from typing import cast

import httpx
import httpx2
import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import AppResources
from app.core.config import Settings
from app.main import create_app
from app.providers.amd.provider import MAX_HTML_BYTES, AmdProvider
from app.services.cached_provider import CachedAnimeProvider

HTML = (Path(__file__).resolve().parents[1] / "fixtures" / "amd_anime.html").read_bytes()
DETAIL_PATH = "/1489-protivostojanie-svjatogo.html"


def call_api(
    handler: Callable[[httpx.Request], httpx.Response], anime_id: str = "amd:1489"
) -> httpx2.Response:
    upstream = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    app = create_app(Settings(environment="test"), anime_provider=AmdProvider(upstream))
    try:
        with TestClient(app) as client:
            return client.get(f"/anime/{anime_id}")
    finally:
        asyncio.run(upstream.aclose())


def redirect() -> httpx.Response:
    return httpx.Response(301, headers={"location": DETAIL_PATH})


def test_fixture_through_http_provider_service_and_api() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/index.php":
            assert dict(request.url.params) == {"newsid": "1489"}
            return redirect()
        assert request.url.path == DETAIL_PATH
        return httpx.Response(
            200, content=HTML, headers={"content-type": "text/html; charset=utf-8"}
        )

    response = call_api(handler)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["id"] == "amd:1489"
    assert data["providerId"] == "1489"
    assert data["title"] == "Противостояние святого"
    assert data["year"] == 2023
    assert data["posterUrl"] == "https://amd.online/uploads/posts/2024-12/original.webp"
    assert data["updatedAt"].endswith("Z")
    assert data["rating"] is None and data["episodeCount"] is None
    assert data["status"] == "UNKNOWN" and data["type"] == "UNKNOWN"
    assert "provider_id" not in data and "poster_url" not in data
    assert len(requests) == 2


@pytest.mark.parametrize(
    ("anime_id", "status"),
    [
        ("invalid", 422),
        ("amd:0", 422),
        ("amd:01489", 422),
        ("amd:abc", 422),
        ("amd:1234567890123", 422),
        ("other:1489", 404),
    ],
)
def test_bad_identity_does_not_make_network_request(anime_id: str, status: int) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        raise AssertionError("Invalid ID must not be fetched")

    assert call_api(handler, anime_id).status_code == status


@pytest.mark.parametrize(
    ("upstream", "status", "code"),
    [
        (404, 404, "NOT_FOUND"),
        (410, 404, "NOT_FOUND"),
        (403, 503, "PROVIDER_UNAVAILABLE"),
        (500, 503, "PROVIDER_UNAVAILABLE"),
        (503, 503, "PROVIDER_UNAVAILABLE"),
        (429, 429, "RATE_LIMITED"),
    ],
)
def test_upstream_status_mapping(upstream: int, status: int, code: str) -> None:
    response = call_api(lambda _: httpx.Response(upstream, headers={"retry-after": "30"}))
    assert response.status_code == status
    assert response.json()["error"]["code"] == code
    assert response.json()["error"]["requestId"] == response.headers["x-request-id"]
    if status == 429:
        assert response.headers["retry-after"] == "30"


@pytest.mark.parametrize("error", [httpx.ReadTimeout, httpx.ConnectError])
def test_transport_error_is_not_not_found(error: type[httpx.RequestError]) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise error("private upstream detail", request=request)

    response = call_api(handler)
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "NETWORK_ERROR"
    assert "private" not in response.text


@pytest.mark.parametrize(
    "target",
    [
        "https://other.example/1489-anime.html",
        "http://amd.online/1489-anime.html",
        "/1490-other.html",
        "/",
        "https://user:pw@amd.online/1489-anime.html",
        "",
    ],
)
def test_redirects_cannot_change_origin_or_identity(target: str) -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(302, headers={"location": target})

    assert call_api(handler).status_code == 503
    assert calls == 1


def test_redirect_loop_is_bounded() -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return redirect()

    assert call_api(handler).status_code == 503
    assert calls == 4


@pytest.mark.parametrize(
    ("body", "media_type"),
    [
        (b"<h1>Broken page</h1>", "text/html"),
        (HTML, "application/json"),
        (b"x" * (MAX_HTML_BYTES + 1), "text/html"),
    ],
)
def test_bad_content_is_parsing_error(body: bytes, media_type: str) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/index.php":
            return redirect()
        return httpx.Response(200, content=body, headers={"content-type": media_type})

    response = call_api(handler)
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "PARSING_ERROR"


def test_default_wiring_uses_lifespan_http_client() -> None:
    app = create_app(Settings(environment="test"))
    with TestClient(app) as client:
        resources = cast(AppResources, app.state.resources)
        assert isinstance(resources.anime_provider, CachedAnimeProvider)
        assert isinstance(resources.anime_provider.provider, AmdProvider)
        assert resources.anime_provider.provider.client is resources.http_client
        assert client.get("/health").status_code == 200
    assert resources.http_client.is_closed
