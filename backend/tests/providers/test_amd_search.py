import asyncio
from pathlib import Path
from urllib.parse import parse_qs

import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.exceptions import ParsingError
from app.main import create_app
from app.providers.amd.provider import AmdProvider
from app.providers.amd.search import parse_search

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def fixture(name: str) -> bytes:
    return (FIXTURES / f"amd_search{name}.html").read_bytes()


@pytest.mark.parametrize(
    ("suffix", "q", "page", "count", "total"),
    [
        ("", "Наруто", 1, 1, 1),
        ("_many", "мир", 1, 10, 191),
        ("_page2", "мир", 2, 10, 191),
        ("_empty", "aurorazzznomatchxyz", 1, 0, 0),
    ],
)
def test_real_search_fixtures(suffix: str, q: str, page: int, count: int, total: int) -> None:
    items, actual = parse_search(fixture(suffix), q, page)
    assert actual == total and len(items) == count
    if suffix == "":
        assert items[0].id == "amd:14"
        assert items[0].title == "Боруто: Новое поколение Наруто"
        assert items[0].rating is None and items[0].year is None
        assert str(items[0].poster_url).startswith("https://amd.online/uploads/")


@pytest.mark.parametrize("mutation", ["count", "card", "page", "echo", "link"])
def test_changed_markup_is_not_empty_success(mutation: str) -> None:
    html = fixture("_many").decode()
    if mutation == "count":
        html = html.replace("search_result_num", "changed_count")
    if mutation == "card":
        html = html.replace("poster__title", "changed_title")
    if mutation == "page":
        html = html.replace("<span>1</span>", "<span>2</span>")
    if mutation == "echo":
        html = html.replace('value="мир"', 'value="other"')
    if mutation == "link":
        html = html.replace('href="https://amd.online/', 'href="https://other.example/')
    with pytest.raises(ParsingError):
        parse_search(html.encode(), "мир", 1)


def test_no_result_requires_explicit_marker() -> None:
    html = fixture("_empty").replace("Новостей по данному запросу не найдено.".encode(), b"changed")
    with pytest.raises(ParsingError):
        parse_search(html, "aurorazzznomatchxyz", 1)


@pytest.mark.parametrize(
    ("page", "size", "expected_count", "has_next", "expected_requests"),
    [
        (1, 20, 20, True, [0, 2]),
        (2, 7, 7, True, [0, 2]),
        (1, 1, 1, True, [0]),
        (100, 20, 0, False, [0]),
    ],
)
def test_api_pagination_aggregates_source_pages(
    page: int, size: int, expected_count: int, has_next: bool, expected_requests: list[int]
) -> None:
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert str(request.url) == "https://amd.online/index.php?do=search"
        form = parse_qs(request.content.decode())
        assert form["story"] == ["мир"]
        number = int(form["from_page"][0])
        calls.append(number)
        return httpx.Response(
            200,
            content=fixture("_many" if number == 0 else "_page2"),
            headers={"content-type": "text/html"},
        )

    upstream = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        app = create_app(Settings(environment="test"), anime_provider=AmdProvider(upstream))
        with TestClient(app) as client:
            response = client.get("/search", params={"q": " мир ", "page": page, "pageSize": size})
        assert response.status_code == 200, response.text
        result = response.json()
        assert len(result["items"]) == expected_count
        assert result["hasNext"] == has_next and result["total"] == 191
        assert result["pageSize"] == size and result["page"] == page
        if page == 2 and size == 7:
            a, _ = parse_search(fixture("_many"), "мир", 1)
            b, _ = parse_search(fixture("_page2"), "мир", 2)
            assert [i["id"] for i in result["items"]] == [i.id for i in (a + b)[7:14]]
        assert calls == expected_requests
    finally:
        asyncio.run(upstream.aclose())


@pytest.mark.parametrize(
    "params",
    [
        {"q": ""},
        {"q": "aa"},
        {"q": "a" * 26},
        {"q": "мир", "page": "0"},
        {"q": "мир", "pageSize": "51"},
        {"q": "мир", "genre": "экшен"},
        {"q": "мир", "year": "2023"},
        {"q": "мир", "rating": "8"},
        {"q": "мир", "sort": "rating"},
        {"q": "мир", "typo": "x"},
    ],
)
def test_invalid_or_unsupported_filters_do_not_fetch(params: dict[str, str]) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        raise AssertionError("Invalid request reached upstream")

    upstream = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        with TestClient(create_app(anime_provider=AmdProvider(upstream))) as client:
            response = client.get("/search", params=params)
        assert response.status_code == 422, response.text
    finally:
        asyncio.run(upstream.aclose())


@pytest.mark.parametrize(
    ("status", "code"),
    [(429, "RATE_LIMITED"), (503, "PROVIDER_UNAVAILABLE"), (302, "PROVIDER_UNAVAILABLE")],
)
def test_search_upstream_errors(status: int, code: str) -> None:
    upstream = httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(status)))
    try:
        with TestClient(create_app(anime_provider=AmdProvider(upstream))) as client:
            response = client.get("/search", params={"q": "мир"})
        assert response.json()["error"]["code"] == code
    finally:
        asyncio.run(upstream.aclose())
