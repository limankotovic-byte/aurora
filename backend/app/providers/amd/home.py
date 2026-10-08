import asyncio
import re
from datetime import UTC, datetime

import httpx
from bs4 import BeautifulSoup, Tag
from pydantic import HttpUrl, ValidationError

from app.core.exceptions import NetworkError, ParsingError, ProviderUnavailable, RateLimited
from app.models.anime import Anime, AnimeStatus
from app.models.catalog import HomeCatalog
from app.models.episode import Episode
from app.models.release import Release
from app.providers.amd import selectors as s
from app.providers.amd.identity import (
    DETAIL_PATH_PATTERN,
    EPISODE_NUMBER_PATTERN,
    ORIGIN,
    episode_id,
    validate_detail_url,
)

HOME_URL = ORIGIN + "/"
ONGOING_URL = ORIGIN + "/ongoingi/"
POPULAR_URL = ORIGIN + "/top-100-1.html"


async def fetch_html(client: httpx.AsyncClient, url: str) -> bytes:
    try:
        async with client.stream("GET", url, follow_redirects=False) as response:
            if response.status_code == 429:
                retry = response.headers.get("retry-after", "")
                raise RateLimited(
                    retry_after=int(retry) if re.fullmatch(r"[0-9]{1,9}", retry) else None
                )
            if response.status_code != 200:
                raise ProviderUnavailable("Catalog source failed")
            if response.headers.get("content-type", "").split(";")[0].strip() != "text/html":
                raise ParsingError("Expected catalog HTML")
            body = bytearray()
            async for chunk in response.aiter_bytes(chunk_size=65536):
                body.extend(chunk)
                if len(body) > 2 * 1024 * 1024:
                    raise ParsingError("Catalog response too large")
            return bytes(body)
    except httpx.RequestError as exc:
        raise NetworkError("Catalog transport failed") from exc


def required(root: Tag, selector: str) -> Tag:
    element = root.select_one(selector)
    if element is None:
        raise ParsingError("Missing catalog section or field")
    return element


def card(link: Tag, title: Tag, image: Tag | None) -> Anime:
    href = link.get("href")
    if not isinstance(href, str):
        raise ParsingError("Missing card link")
    try:
        url = httpx.URL(ORIGIN).join(href)
        match = re.fullmatch(DETAIL_PATH_PATTERN, url.path)
        if match is None:
            raise ParsingError("Invalid catalog identity")
        validate_detail_url(url, match[1])
    except (httpx.InvalidURL, ProviderUnavailable) as exc:
        raise ParsingError("Invalid catalog URL") from exc
    text = " ".join(title.get_text(" ", strip=True).split())
    if not text:
        raise ParsingError("Empty catalog title")
    poster: HttpUrl | None = None
    src = image.get("src") if image else None
    if isinstance(src, str) and src.strip():
        try:
            poster = HttpUrl(str(httpx.URL(ORIGIN).join(src)))
            if poster.username or poster.password:
                poster = None
        except (httpx.InvalidURL, ValidationError):
            poster = None
    return Anime(
        id=f"amd:{match[1]}",
        provider="amd",
        provider_id=match[1],
        title=text,
        poster_url=poster,
        updated_at=datetime.now(UTC),
    )


def posters(root: Tag) -> list[Anime]:
    rows = root.select(s.HOME_POSTERS)
    if not rows:
        raise ParsingError("Empty or changed catalog poster section")
    result = [
        card(
            required(row, s.SEARCH_LINK),
            required(row, s.SEARCH_TITLE),
            row.select_one(s.SEARCH_POSTER),
        )
        for row in rows
    ]
    return list({item.id: item for item in result}.values())


def parse_releases(html: bytes) -> list[Release]:
    soup = BeautifulSoup(html, "html.parser")
    rows = required(soup, s.HOME_RELEASES).select(s.RELEASE_ROWS)
    if not rows:
        raise ParsingError("Missing latest episode rows")
    releases: list[Release] = []
    for row in rows:
        anime = card(row, required(row, s.RELEASE_TITLE), row.select_one(s.RELEASE_IMAGE))
        number = required(row, s.RELEASE_NUMBER).get_text(strip=True)
        if re.fullmatch(EPISODE_NUMBER_PATTERN, number) is None:
            raise ParsingError("Unsupported episode number in release feed")
        episode = Episode(
            id=episode_id(anime.provider_id, number), anime_id=anime.id, number=float(number)
        )
        releases.append(Release(anime=anime, episode=episode, provider="amd"))
    if len({release.episode.id for release in releases}) != len(releases):
        raise ParsingError("Duplicate release identities")
    return releases


def parse_home(home: bytes, ongoing: bytes, popular: bytes) -> HomeCatalog:
    root = BeautifulSoup(home, "html.parser")
    ongoing_root = required(BeautifulSoup(ongoing, "html.parser"), s.CATALOG_ROOT)
    popular_root = required(BeautifulSoup(popular, "html.parser"), s.CATALOG_ROOT)
    ongoing_items = posters(ongoing_root)
    for anime in ongoing_items:
        anime.status = AnimeStatus.ONGOING
    ranked = popular_root.select(s.POPULAR_ROWS)
    if not ranked:
        raise ParsingError("Missing popular catalog rows")
    return HomeCatalog(
        featured=posters(required(root, s.HOME_FEATURED)),
        new_releases=posters(required(root, s.HOME_NEW)),
        latest=parse_releases(home),
        ongoing=ongoing_items,
        popular=[
            card(row, required(row, s.POPULAR_TITLE), row.select_one(s.POPULAR_IMAGE))
            for row in ranked[:20]
        ],
    )


async def get_home(client: httpx.AsyncClient) -> HomeCatalog:
    # Sequential fetches avoid orphaned sibling requests if one source fails.
    home = await fetch_html(client, HOME_URL)
    ongoing = await fetch_html(client, ONGOING_URL)
    popular = await fetch_html(client, POPULAR_URL)
    return await asyncio.to_thread(parse_home, home, ongoing, popular)
