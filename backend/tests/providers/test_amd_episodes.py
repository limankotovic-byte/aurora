import asyncio
from collections.abc import Callable
from pathlib import Path

import httpx
import httpx2
import pytest
from bs4 import BeautifulSoup
from fastapi.testclient import TestClient

from app.core.exceptions import ParsingError
from app.main import create_app
from app.providers.amd.episodes import parse_episodes
from app.providers.amd.home import parse_releases
from app.providers.amd.provider import AmdProvider

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
HTML = (FIXTURES / "amd_episodes_5781.html").read_bytes()
DETAIL_PATH = "/5781-magija-vernuvshegosja-dolzhna-byt-osobennoj-2.html"


@pytest.mark.parametrize(
    ("aid", "count"), [("1489", 162), ("5781", 2), ("1925", 1), ("5796", 5), ("5790", 0)]
)
def test_real_navigation_including_movie_ova_and_announcement(aid: str, count: int) -> None:
    episodes = parse_episodes(
        (FIXTURES / f"amd_episodes_{aid}.html").read_bytes(), anime_id=f"amd:{aid}"
    )
    assert len(episodes) == count
    assert [e.number for e in episodes] == list(range(1, count + 1))
    assert [e.id for e in episodes] == [f"amd:{aid}-episode-{n}" for n in range(1, count + 1)]
    assert all(e.anime_id == f"amd:{aid}" for e in episodes)
    assert all(e.season is None and e.release_date is None and e.title is None for e in episodes)
    assert all(not e.available and e.player_id is None for e in episodes)


def test_episode_identity_matches_home_release_and_ignores_slug() -> None:
    expected = parse_episodes(HTML, anime_id="amd:5781")
    release = parse_releases((FIXTURES / "amd_home.html").read_bytes())[0]
    assert expected[0].id == release.episode.id
    changed = HTML.replace(b"magija-vernuvshegosja-dolzhna-byt-osobennoj-2", b"renamed-title")
    assert parse_episodes(changed, anime_id="amd:5781") == expected


def test_duplicate_copies_and_source_sort_do_not_change_pagination_order() -> None:
    soup = BeautifulSoup((FIXTURES / "amd_episodes_1489.html").read_bytes(), "html.parser")
    for root in soup.select("#elementb"):
        for link in reversed(root.select("a")):
            root.append(link.extract())
    result = parse_episodes(str(soup).encode(), anime_id="amd:1489")
    assert len(result) == 162
    assert [e.number for e in result[8:12]] == [9, 10, 11, 12]
    # Source lists the upcoming 162nd row, not all 180 planned episodes.
    assert result[-1].number == 162 and not result[-1].available


@pytest.mark.parametrize(
    ("old", "new"),
    [
        (b"pmovie__player", b"changed-player"),
        (b"amd-card", b"changed-card"),
        (b' id="elementb"', b' id="changed"'),
        (b"nav_video_links", b"changed-link"),
        (b'data-vid="1"', b'data-vid="01"'),
        (b'data-vid="1"', b'data-vid="1.5"'),
        (b'data-vid="1"', b'data-vid="special"'),
        (b">1</a>", b">Special</a>"),
        (b"/episode/1/", b"/episode/2/"),
        (b"https://amd.online/5781-", b"https://amd.online/5782-"),
        (b"https://amd.online/5781-", b"https://other.example/5781-"),
        (b"https://amd.online/5781-", b"https://user:pw@amd.online/5781-"),
        (b'seriya-onlayn.html"', b'seriya-onlayn.html?query=1"'),
    ],
)
def test_changed_or_inconsistent_navigation_is_error(old: bytes, new: bytes) -> None:
    assert old in HTML
    with pytest.raises(ParsingError):
        parse_episodes(HTML.replace(old, new), anime_id="amd:5781")


@pytest.mark.parametrize("change", ["missing_copy_row", "duplicate_row", "empty_list"])
def test_conflicting_or_duplicate_rows_are_not_silently_dropped(change: str) -> None:
    soup = BeautifulSoup(HTML, "html.parser")
    roots = soup.select("#elementb")
    links = roots[0].select("a")
    if change == "missing_copy_row":
        links[-1].decompose()
    elif change == "empty_list":
        roots[0].clear()
    else:
        roots[0].append(BeautifulSoup(str(links[0]), "html.parser"))
    with pytest.raises(ParsingError):
        parse_episodes(str(soup).encode(), anime_id="amd:5781")


@pytest.mark.parametrize(
    ("old", "new"),
    [(b"/anonsy/", b"/zavershennye/"), (b"<span>-</span>", b"<span>1</span>")],
)
def test_empty_result_requires_explicit_announcement(old: bytes, new: bytes) -> None:
    html = (FIXTURES / "amd_episodes_5790.html").read_bytes()
    assert old in html
    with pytest.raises(ParsingError):
        parse_episodes(html.replace(old, new), anime_id="amd:5790")


def call_api(
    handler: Callable[[httpx.Request], httpx.Response], path: str = "amd:5781/episodes"
) -> httpx2.Response:
    upstream = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        with TestClient(create_app(anime_provider=AmdProvider(upstream))) as client:
            return client.get(f"/anime/{path}")
    finally:
        asyncio.run(upstream.aclose())


def test_http_provider_route_pagination_cache_and_camelcase() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if request.url.path == "/index.php":
            assert dict(request.url.params) == {"newsid": "5781"}
            return httpx.Response(301, headers={"location": DETAIL_PATH})
        assert request.url.path == DETAIL_PATH
        return httpx.Response(200, content=HTML, headers={"content-type": "text/html"})

    upstream = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        with TestClient(create_app(anime_provider=AmdProvider(upstream))) as client:
            path = "/anime/amd:5781/episodes?pageSize=1"
            first = client.get(path)
            assert first.status_code == 200, first.text
            data = first.json()
            assert data["page"] == 1 and data["pageSize"] == 1 and data["hasNext"]
            assert data["total"] == 2 and len(data["items"]) == 1
            episode = data["items"][0]
            assert episode["id"] == "amd:5781-episode-1" and episode["animeId"] == "amd:5781"
            assert episode["number"] == 1 and episode["season"] is None
            assert episode["playerId"] is None and not episode["available"]
            assert "anime_id" not in episode and "release_date" not in episode
            assert client.get(path).json() == data and len(calls) == 2
            second = client.get(path + "&page=2").json()
            assert second["items"][0]["id"] == "amd:5781-episode-2"
            assert not second["hasNext"] and len(calls) == 4
            empty = client.get(path + "&page=3").json()
            assert empty["items"] == [] and not empty["hasNext"] and empty["total"] == 2
    finally:
        asyncio.run(upstream.aclose())


@pytest.mark.parametrize(
    ("path", "status", "code"),
    [
        ("bad/episodes", 422, "VALIDATION_ERROR"),
        ("amd:0/episodes", 422, "VALIDATION_ERROR"),
        ("amd:abc/episodes", 422, "VALIDATION_ERROR"),
        ("other:5781/episodes", 404, "NOT_FOUND"),
        ("amd:5781/episodes?page=0", 422, "VALIDATION_ERROR"),
        ("amd:5781/episodes?pageSize=51", 422, "VALIDATION_ERROR"),
        ("amd:5781/episodes?season=-1", 422, "VALIDATION_ERROR"),
        ("amd:5781/episodes?season=1.5", 422, "VALIDATION_ERROR"),
        ("amd:5781/episodes?season=0", 422, "UNSUPPORTED_OPERATION"),
        ("amd:5781/episodes?season=2", 422, "UNSUPPORTED_OPERATION"),
        ("amd:5781/episodes?sort=desc", 422, "VALIDATION_ERROR"),
    ],
)
def test_bad_id_query_or_unsupported_season_never_fetches(
    path: str, status: int, code: str
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("Invalid input must not reach upstream")

    response = call_api(handler, path)
    assert response.status_code == status
    assert response.json()["error"]["code"] == code


@pytest.mark.parametrize(
    ("upstream_status", "status", "code"),
    [(404, 404, "NOT_FOUND"), (429, 429, "RATE_LIMITED"), (503, 503, "PROVIDER_UNAVAILABLE")],
)
def test_episode_api_preserves_source_failures(
    upstream_status: int, status: int, code: str
) -> None:
    response = call_api(lambda _: httpx.Response(upstream_status, headers={"retry-after": "30"}))
    assert response.status_code == status and response.json()["error"]["code"] == code
    assert response.json()["error"]["requestId"] == response.headers["x-request-id"]
    if status == 429:
        assert response.headers["retry-after"] == "30"


def test_episode_api_transport_failure() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("private upstream message", request=request)

    response = call_api(handler)
    assert response.status_code == 502 and response.json()["error"]["code"] == "NETWORK_ERROR"
    assert "private" not in response.text


def test_episode_api_parser_failure_is_not_empty_page() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/index.php":
            return httpx.Response(301, headers={"location": DETAIL_PATH})
        return httpx.Response(
            200, text="<html>changed</html>", headers={"content-type": "text/html"}
        )

    response = call_api(handler)
    assert response.status_code == 502 and response.json()["error"]["code"] == "PARSING_ERROR"
