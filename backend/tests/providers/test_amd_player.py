import asyncio
import hashlib
import json
from collections.abc import Callable
from pathlib import Path

import httpx
import pytest
from bs4 import BeautifulSoup

from app.core.exceptions import (
    InvalidEpisodeId,
    NetworkError,
    NotFound,
    ParsingError,
    PlayerUnavailable,
    ProviderUnavailable,
    RateLimited,
)
from app.models.player import WebEmbedPlayerInfo
from app.providers.amd.pages import MAX_HTML_BYTES
from app.providers.amd.player import AmdPlayerProvider, episode_page_url, parse_player_page
from app.providers.base import PlayerProvider

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
RUTUBE = (FIXTURES / "amd_player_1489_2.html").read_bytes()
KODIK = (FIXTURES / "amd_player_5796_3.html").read_bytes()
RUTUBE_URL = "https://rutube.ru/play/embed/d791bbe24544e24369f260d348643c15"


@pytest.mark.parametrize(
    ("aid", "number", "host"),
    [
        ("1489", "2", "rutube.ru"),
        ("5781", "1", "kodikplayer.com"),
        ("5796", "3", "kodikplayer.com"),
        ("1925", "1", "vk.com"),
    ],
)
def test_real_source_embed_mapping_and_conservative_capabilities(
    aid: str, number: str, host: str
) -> None:
    info = parse_player_page(
        (FIXTURES / f"amd_player_{aid}_{number}.html").read_bytes(),
        episode_id=f"amd:{aid}-episode-{number}",
    )
    assert info.type == "WEB_EMBED" and info.provider == "amd"
    assert info.embed_url.scheme == "https" and info.embed_url.host == host
    assert info.quality_hint is None  # /720p is not a promise of actual playback quality.
    assert info.capabilities.model_dump() == {"progress": False, "seek": False, "fullscreen": False}


@pytest.mark.parametrize(("aid", "number"), [("1489", "162"), ("5781", "2")])
def test_upcoming_episode_placeholder_is_unavailable_not_an_embed(aid: str, number: str) -> None:
    with pytest.raises(PlayerUnavailable):
        parse_player_page(
            (FIXTURES / f"amd_player_{aid}_{number}.html").read_bytes(),
            episode_id=f"amd:{aid}-episode-{number}",
        )


def test_aser_is_supported_as_source_iframe_when_no_kodik_candidate() -> None:
    soup = BeautifulSoup((FIXTURES / "amd_player_5781_1.html").read_bytes(), "html.parser")
    for node in soup.select("button[data-player='kodik'], iframe.amd-kodik-iframe"):
        node.decompose()
    result = parse_player_page(str(soup).encode(), episode_id="amd:5781-episode-1")
    assert str(result.embed_url) == "https://aser.pro/vod/48095"


def test_source_and_fixture_provenance_is_complete() -> None:
    sources = json.loads((FIXTURES / "amd_player_sources.json").read_text())
    assert len(sources) == 6
    for item in sources:
        assert item["http_status"] == 200 and item["url"].startswith("https://amd.online/")
        assert item["source_bytes"] > 100000 and len(item["source_sha256"]) == 64
        body = (FIXTURES / item["fixture"]).read_bytes()
        assert hashlib.sha256(body).hexdigest() == item["fixture_sha256"]
        if item["result"] == "PLAYER_UNAVAILABLE":
            with pytest.raises(PlayerUnavailable):
                parse_player_page(body, episode_id=item["episode_id"])
        else:
            assert (
                parse_player_page(body, episode_id=item["episode_id"]).model_dump(mode="json")
                == item["result"]
            )


def test_page_url_comes_from_navigation_and_is_slug_independent() -> None:
    html = (FIXTURES / "amd_episodes_1489.html").read_bytes()
    url = episode_page_url(html, episode_id="amd:1489-episode-2")
    assert (
        str(url) == "https://amd.online/1489-protivostojanie-svjatogo/episode/2/seriya-onlayn.html"
    )
    renamed = html.replace(b"protivostojanie-svjatogo", b"renamed")
    assert "/1489-renamed/episode/2/" in str(
        episode_page_url(renamed, episode_id="amd:1489-episode-2")
    )


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "file:///etc/passwd",
        "http://127.0.0.1/private",
        "https://127.0.0.1/private",
        "https://rutube.ru.evil.example/play/embed/" + "a" * 32,
        RUTUBE_URL.replace("https:", "http:"),
        RUTUBE_URL.replace("rutube.ru", "user:pw@rutube.ru"),
        RUTUBE_URL.replace("rutube.ru", "rutube.ru:8443"),
        RUTUBE_URL + "#unsafe",
        RUTUBE_URL + "?p=private-key",
        "https://rutube.ru/video/" + "a" * 32,
        "https://example.com/video.mp4",
        "https://example.com/video.m3u8",
        "/index.php?do=nz&id=1489",
        "https://rutube.ru/" + "x" * 2050,
    ],
)
def test_unreviewed_unsafe_or_direct_media_url_is_never_returned(url: str) -> None:
    soup = BeautifulSoup(RUTUBE, "html.parser")
    for link in soup.select("a.sel-active"):
        link["data-vlnk"] = url
    for frame in soup.select("iframe.frame_video_mod"):
        frame["src"] = url
    with pytest.raises(PlayerUnavailable):
        parse_player_page(str(soup).encode(), episode_id="amd:1489-episode-2")


@pytest.mark.parametrize(
    "change",
    [
        "wrong_selected",
        "multiple_active",
        "conflicting_links",
        "conflicting_frames",
        "missing_frame",
        "missing_player",
        "conflicting_lazy_frame",
    ],
)
def test_selected_episode_and_iframe_must_agree(change: str) -> None:
    soup = BeautifulSoup(RUTUBE, "html.parser")
    if change == "wrong_selected":
        for link in soup.select("a.sel-active"):
            link["class"] = "nav_video_links"
        for link in soup.select("a[data-vid='1']"):
            link["class"] = "nav_video_links sel-active"
    elif change == "multiple_active":
        soup.select_one("a[data-vid='1']")["class"] = "nav_video_links sel-active"  # type: ignore[index]
    elif change == "conflicting_links":
        soup.select_one("a.sel-active")["data-vlnk"] = RUTUBE_URL + "?other=1"  # type: ignore[index]
    elif change == "conflicting_frames":
        soup.select_one("iframe")["src"] = RUTUBE_URL + "?other=1"  # type: ignore[index]
    elif change == "missing_frame":
        for frame in soup.select("iframe"):
            frame.decompose()
    elif change == "missing_player":
        soup.select_one(".pmovie__player").decompose()  # type: ignore[union-attr]
    else:
        soup.select_one("iframe")["data-src"] = RUTUBE_URL + "?other=1"  # type: ignore[index]
    with pytest.raises(ParsingError):
        parse_player_page(str(soup).encode(), episode_id="amd:1489-episode-2")


@pytest.mark.parametrize("change", ["episode", "flag", "missing_button", "conflict"])
def test_kodik_episode_flag_and_iframe_copies_are_checked(change: str) -> None:
    soup = BeautifulSoup(KODIK, "html.parser")
    frames = soup.select("iframe")
    button = soup.select_one("button[data-player='kodik']")
    assert button is not None
    if change == "episode":
        for frame in frames:
            frame["data-src"] = str(frame["data-src"]).replace("episode=3", "episode=2")
    elif change == "flag":
        button["data-has-ep"] = "0"
    elif change == "missing_button":
        button.decompose()
    else:
        frames[0]["data-src"] = str(frames[0]["data-src"]).replace("season=1", "season=2")
    with pytest.raises(ParsingError):
        parse_player_page(str(soup).encode(), episode_id="amd:5796-episode-3")


def resolve(
    handler: Callable[[httpx.Request], httpx.Response], episode_id: str = "amd:1489-episode-2"
) -> WebEmbedPlayerInfo:
    async def run() -> WebEmbedPlayerInfo:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider: PlayerProvider = AmdPlayerProvider(client)
            result = await provider.get_player(episode_id)
            assert isinstance(result, WebEmbedPlayerInfo)
            return result

    return asyncio.run(run())


def source_handler(requests: list[httpx.Request]) -> Callable[[httpx.Request], httpx.Response]:
    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert request.url.host == "amd.online", "Resolver must never request a vendor/media URL"
        if request.url.path == "/index.php":
            assert dict(request.url.params) == {"newsid": "1489"}
            return httpx.Response(301, headers={"location": "/1489-renamed.html"})
        if request.url.path == "/1489-renamed.html":
            body = (FIXTURES / "amd_episodes_1489.html").read_bytes()
        else:
            assert request.url.path == "/1489-protivostojanie-svjatogo/episode/2/seriya-onlayn.html"
            body = RUTUBE
        return httpx.Response(200, content=body, headers={"content-type": "text/html"})

    return handler


def test_provider_resolves_source_only_and_implements_independent_protocol() -> None:
    requests: list[httpx.Request] = []
    assert str(resolve(source_handler(requests)).embed_url) == RUTUBE_URL
    assert len(requests) == 3


@pytest.mark.parametrize(
    "episode_id",
    [
        "invalid",
        "amd:1489",
        "amd:0-episode-1",
        "amd:01489-episode-1",
        "amd:1489-episode-0",
        "amd:1489-episode-01",
        "amd:1489-episode-1.5",
        "amd:1489-episode-special",
        "amd:1234567890123-episode-1",
    ],
)
def test_invalid_episode_ids_never_make_requests(episode_id: str) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("Invalid episode ID must not be fetched")

    with pytest.raises(InvalidEpisodeId):
        resolve(handler, episode_id)


def test_unknown_namespace_and_missing_episode_are_not_found() -> None:
    requests: list[httpx.Request] = []
    with pytest.raises(NotFound):
        resolve(source_handler(requests), "other:1489-episode-2")
    assert not requests
    with pytest.raises(NotFound):
        resolve(source_handler(requests), "amd:1489-episode-999")
    assert len(requests) == 2  # No guessed episode page request.


@pytest.mark.parametrize(
    "location",
    [
        "https://other.example/1489-x/episode/2/seriya-onlayn.html",
        "/1489-x/episode/3/seriya-onlayn.html",
        "/1490-x/episode/2/seriya-onlayn.html",
        "/1489-x.html",
        "http://amd.online/1489-x/episode/2/seriya-onlayn.html",
        "https://user:pw@amd.online/1489-x/episode/2/seriya-onlayn.html",
    ],
)
def test_episode_redirect_cannot_change_origin_anime_or_episode(location: str) -> None:
    requests: list[httpx.Request] = []
    base = source_handler(requests)

    def handler(request: httpx.Request) -> httpx.Response:
        response = base(request)
        if "/episode/" in request.url.path:
            return httpx.Response(302, headers={"location": location})
        return response

    with pytest.raises(ProviderUnavailable):
        resolve(handler)
    assert len(requests) == 3


@pytest.mark.parametrize(
    ("status", "error"),
    [
        (404, NotFound),
        (410, NotFound),
        (429, RateLimited),
        (403, ProviderUnavailable),
        (503, ProviderUnavailable),
    ],
)
def test_episode_page_http_failures_are_not_swallowed(status: int, error: type[Exception]) -> None:
    base = source_handler([])

    def handler(request: httpx.Request) -> httpx.Response:
        if "/episode/" in request.url.path:
            return httpx.Response(status, headers={"retry-after": "15"})
        return base(request)

    with pytest.raises(error) as exc:
        resolve(handler)
    if isinstance(exc.value, RateLimited):
        assert exc.value.retry_after == 15


@pytest.mark.parametrize("change", ["timeout", "media_type", "oversize", "redirect_loop"])
def test_episode_page_transport_content_and_redirect_limits(change: str) -> None:
    base = source_handler([])

    def handler(request: httpx.Request) -> httpx.Response:
        if "/episode/" not in request.url.path:
            return base(request)
        if change == "timeout":
            raise httpx.ReadTimeout("private error", request=request)
        if change == "redirect_loop":
            return httpx.Response(302, headers={"location": str(request.url)})
        return httpx.Response(
            200,
            content=b"x" * (MAX_HTML_BYTES + 1) if change == "oversize" else RUTUBE,
            headers={"content-type": "application/json" if change == "media_type" else "text/html"},
        )

    error = (
        NetworkError
        if change == "timeout"
        else ProviderUnavailable
        if change == "redirect_loop"
        else ParsingError
    )
    with pytest.raises(error):
        resolve(handler)


def test_supports_embed_and_nullable_url_do_not_hide_upstream_or_parser_errors() -> None:
    async def run() -> None:
        base = source_handler([])

        def unavailable(request: httpx.Request) -> httpx.Response:
            if "/episode/" in request.url.path:
                body = (FIXTURES / "amd_player_1489_162.html").read_bytes()
                return httpx.Response(200, content=body, headers={"content-type": "text/html"})
            return base(request)

        # The requested page must select the requested episode, even for a stub.
        async with httpx.AsyncClient(transport=httpx.MockTransport(unavailable)) as client:
            with pytest.raises(ParsingError):
                await AmdPlayerProvider(client).supports_embed("amd:1489-episode-2")

        def placeholder(request: httpx.Request) -> httpx.Response:
            response = base(request)
            if "/episode/" in request.url.path:
                body = RUTUBE.replace(RUTUBE_URL.encode(), b"/index.php?do=nz&amp;id=1489")
                return httpx.Response(200, content=body, headers={"content-type": "text/html"})
            return response

        async with httpx.AsyncClient(transport=httpx.MockTransport(placeholder)) as client:
            provider = AmdPlayerProvider(client)
            assert not await provider.supports_embed("amd:1489-episode-2")
            assert await provider.get_embed_url("amd:1489-episode-2") is None
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda _: httpx.Response(503))
        ) as client:
            with pytest.raises(ProviderUnavailable):
                await AmdPlayerProvider(client).supports_embed("amd:1489-episode-2")
        async with httpx.AsyncClient(transport=httpx.MockTransport(base)) as client:
            provider = AmdPlayerProvider(client)
            assert await provider.supports_embed("amd:1489-episode-2")
            assert str(await provider.get_embed_url("amd:1489-episode-2")) == RUTUBE_URL

    asyncio.run(run())
