import asyncio
import re
from datetime import UTC, datetime

import httpx
from bs4 import BeautifulSoup
from pydantic import HttpUrl, ValidationError

from app.core.exceptions import (
    InvalidSearchQuery,
    NetworkError,
    ParsingError,
    ProviderUnavailable,
    RateLimited,
    UnsupportedOperation,
)
from app.models.anime import Anime
from app.models.catalog import Page, SearchQuery
from app.providers.amd import selectors
from app.providers.amd.identity import DETAIL_PATH_PATTERN, ORIGIN, validate_detail_url

SOURCE_PAGE_SIZE = 10
SEARCH_URL = f"{ORIGIN}/index.php?do=search"
MAX_SEARCH_BYTES = 2 * 1024 * 1024


def parse_search(html: bytes, query: str, page: int) -> tuple[list[Anime], int]:
    soup = BeautifulSoup(html, "html.parser")
    root = soup.select_one(selectors.SEARCH_ROOT)
    if root is None:
        raise ParsingError("Missing search root")
    form = root.select_one(selectors.SEARCH_FORM)
    if form is None or form.get("value") != query:
        raise ParsingError("Search query echo mismatch")
    cards = root.select(selectors.SEARCH_CARDS)
    count = root.select_one(selectors.SEARCH_COUNT)
    if count is None:
        empty = soup.select_one(selectors.SEARCH_EMPTY)
        if not cards and empty and empty.get_text(" ", strip=True) == selectors.SEARCH_EMPTY_TEXT:
            return [], 0
        raise ParsingError("Missing explicit search result count")
    match = re.fullmatch(selectors.SEARCH_COUNT_PATTERN, count.get_text(" ", strip=True))
    if match is None:
        raise ParsingError("Invalid search count")
    total = int(match[1])
    current = root.select_one(selectors.SEARCH_CURRENT_PAGE)
    if total > SOURCE_PAGE_SIZE and (current is None or current.get_text(strip=True) != str(page)):
        raise ParsingError("Search page mismatch")
    expected = min(SOURCE_PAGE_SIZE, max(0, total - (page - 1) * SOURCE_PAGE_SIZE))
    if len(cards) != expected:
        raise ParsingError("Incomplete search page")
    items: list[Anime] = []
    for card in cards:
        link = card.select_one(selectors.SEARCH_LINK)
        title = card.select_one(selectors.SEARCH_TITLE)
        href = link.get("href") if link else None
        if not isinstance(href, str) or title is None or not title.get_text(strip=True):
            raise ParsingError("Invalid search card")
        try:
            url = httpx.URL(ORIGIN).join(href)
            identity = re.fullmatch(DETAIL_PATH_PATTERN, url.path)
            if identity is None:
                raise ParsingError("Invalid result identity")
            validate_detail_url(url, identity[1])
        except (httpx.InvalidURL, ProviderUnavailable) as exc:
            raise ParsingError("Invalid result URL") from exc
        poster: HttpUrl | None = None
        image = card.select_one(selectors.SEARCH_POSTER)
        src = image.get("src") if image else None
        if isinstance(src, str) and src.strip():
            try:
                poster = HttpUrl(str(httpx.URL(ORIGIN).join(src)))
                if poster.username is not None or poster.password is not None:
                    poster = None
            except (httpx.InvalidURL, ValidationError):
                poster = None
        items.append(
            Anime(
                id=f"amd:{identity[1]}",
                provider="amd",
                provider_id=identity[1],
                title=" ".join(title.get_text(" ", strip=True).split()),
                poster_url=poster,
                updated_at=datetime.now(UTC),
            )
        )
    if len({item.id for item in items}) != len(items):
        raise ParsingError("Duplicate search identities")
    return items, total


async def search(client: httpx.AsyncClient, query: SearchQuery) -> Page[Anime]:
    if not 3 <= len(query.q) <= 25:
        raise InvalidSearchQuery()
    if any(
        value is not None
        for key, value in query.model_dump().items()
        if key not in ("q", "page", "page_size")
    ):
        raise UnsupportedOperation("AMD search does not expose metadata filters")

    async def fetch(page: int) -> tuple[list[Anime], int]:
        try:
            async with client.stream(
                "POST",
                SEARCH_URL,
                follow_redirects=False,
                data={
                    "do": "search",
                    "subaction": "search",
                    "story": query.q,
                    "from_page": str(page if page > 1 else 0),
                },
            ) as response:
                if response.status_code == 429:
                    retry = response.headers.get("retry-after", "")
                    seconds = int(retry) if re.fullmatch(r"[0-9]{1,9}", retry) else None
                    raise RateLimited(retry_after=seconds)
                if response.status_code != 200:
                    raise ProviderUnavailable("AMD search failed")
                if response.headers.get("content-type", "").split(";")[0].strip() != "text/html":
                    raise ParsingError("Expected search HTML")
                body = bytearray()
                async for chunk in response.aiter_bytes(chunk_size=65536):
                    body.extend(chunk)
                    if len(body) > MAX_SEARCH_BYTES:
                        raise ParsingError("Search response too large")
                return await asyncio.to_thread(parse_search, bytes(body), query.q, page)
        except httpx.RequestError as exc:
            raise NetworkError("Search transport failed") from exc

    first, total = await fetch(1)
    start = (query.page - 1) * query.page_size
    end = min(start + query.page_size, total)
    items: list[Anime] = []
    if start < total:
        for source_page in range(start // SOURCE_PAGE_SIZE + 1, (end - 1) // SOURCE_PAGE_SIZE + 2):
            batch, observed_total = (first, total) if source_page == 1 else await fetch(source_page)
            if observed_total != total:
                raise ParsingError("Search results changed during pagination")
            offset = (source_page - 1) * SOURCE_PAGE_SIZE
            items.extend(batch[max(0, start - offset) : min(SOURCE_PAGE_SIZE, end - offset)])
    if len({item.id for item in items}) != len(items):
        raise ParsingError("Search results shifted during pagination")
    return Page[Anime](
        items=items, page=query.page, page_size=query.page_size, has_next=end < total, total=total
    )
