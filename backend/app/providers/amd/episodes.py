import re

import httpx
from bs4 import BeautifulSoup, Tag

from app.core.exceptions import ParsingError
from app.models.episode import Episode
from app.providers.amd import selectors as s
from app.providers.amd.identity import (
    EPISODE_NUMBER_PATTERN,
    EPISODE_PATH_PATTERN,
    ORIGIN,
    episode_id,
    source_id,
)


def _number(link: Tag, provider_id: str) -> str:
    number, href = link.get("data-vid"), link.get("href")
    if (
        not isinstance(number, str)
        or re.fullmatch(EPISODE_NUMBER_PATTERN, number) is None
        or not isinstance(href, str)
        or link.get_text(" ", strip=True) != number
    ):
        raise ParsingError("Unsupported or inconsistent AMD episode label")
    try:
        url = httpx.URL(ORIGIN).join(href)
    except httpx.InvalidURL as exc:
        raise ParsingError("Invalid episode page URL") from exc
    match = re.fullmatch(EPISODE_PATH_PATTERN, url.path)
    if (
        url.scheme != "https"
        or url.host != "amd.online"
        or url.port not in (None, 443)
        or url.userinfo
        or url.query
        or url.fragment
        or match is None
        or match[1] != provider_id
        or match[2] != number
    ):
        raise ParsingError("Episode link changed origin or identity")
    return number


def _is_announcement(card: Tag) -> bool:
    counts = card.select(s.RELEASED_NUMBER)
    if len(counts) != 1 or counts[0].get_text(strip=True) != "-":
        return False
    for link in card.select(s.ANNOUNCEMENT_LINKS):
        href = link.get("href")
        if not isinstance(href, str):
            continue
        try:
            url = httpx.URL(ORIGIN).join(href)
        except httpx.InvalidURL:
            continue
        if str(url) == ORIGIN + "/anonsy/" and link.get_text(strip=True) == "Анонсы":
            return True
    return False


def parse_episodes(html: bytes, *, anime_id: str) -> list[Episode]:
    """Read public episode navigation only, without inferring playback or seasons."""
    provider_id = source_id(anime_id)
    soup = BeautifulSoup(html, "html.parser")
    for node in soup.select(s.NON_CONTENT):
        node.decompose()
    cards, players = soup.select(s.DETAILS_ROOT), soup.select(s.EPISODE_PLAYER)
    if len(cards) != 1 or len(players) != 1:
        raise ParsingError("Missing or ambiguous AMD episode page")
    player = players[0]
    lists = player.select(s.EPISODE_LISTS)
    if not lists:
        if not player.select(s.EPISODE_LINKS) and _is_announcement(cards[0]):
            return []
        raise ParsingError("Missing episode navigation without explicit announcement")

    numbers: set[str] | None = None
    for container in lists:
        links = container.select(s.EPISODE_LINKS)
        if not links or len(links) != len(container.select("a")):
            raise ParsingError("Empty or changed episode navigation")
        current = [_number(link, provider_id) for link in links]
        unique = set(current)
        if len(unique) != len(current):
            raise ParsingError("Duplicate episode in one navigation list")
        if numbers is not None and unique != numbers:
            raise ParsingError("Conflicting episode navigation copies")
        numbers = unique

    return [
        Episode(id=episode_id(provider_id, number), anime_id=anime_id, number=float(number))
        for number in sorted(numbers or (), key=int)
    ]
