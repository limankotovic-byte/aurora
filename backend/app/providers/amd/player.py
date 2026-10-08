import asyncio
import re

import httpx
from bs4 import BeautifulSoup, Tag
from pydantic import HttpUrl

from app.core.exceptions import NotFound, ParsingError, PlayerUnavailable
from app.models.player import WebEmbedPlayerInfo
from app.providers.amd import selectors as s
from app.providers.amd.episodes import parse_episodes
from app.providers.amd.identity import ORIGIN, episode_identity
from app.providers.amd.pages import fetch_detail_html, fetch_episode_html


def _navigation(html: bytes, episode_id: str) -> tuple[Tag, list[Tag], str, str]:
    provider_id, number = episode_identity(episode_id)
    episodes = parse_episodes(html, anime_id=f"amd:{provider_id}")
    if not any(item.id == episode_id for item in episodes):
        raise NotFound("Episode is not in the public navigation")
    soup = BeautifulSoup(html, "html.parser")
    for node in soup.select(s.NON_CONTENT):
        node.decompose()
    player = soup.select_one(s.EPISODE_PLAYER)
    assert player is not None  # parse_episodes already validated the scoped player.
    links = [link for link in player.select(s.EPISODE_LINKS) if link.get("data-vid") == number]
    return player, links, provider_id, number


def episode_page_url(html: bytes, *, episode_id: str) -> httpx.URL:
    _, links, _, _ = _navigation(html, episode_id)
    urls = {str(httpx.URL(ORIGIN).join(str(link["href"]))) for link in links}
    if len(urls) != 1:
        raise ParsingError("Episode navigation copies disagree on page URL")
    return httpx.URL(urls.pop())


def _placeholder(value: str, provider_id: str) -> bool:
    url = httpx.URL(ORIGIN).join(value)
    return (
        url.scheme == "https"
        and url.host == "amd.online"
        and url.port in (None, 443)
        and not url.userinfo
        and not url.fragment
        and url.path == "/index.php"
        and sorted(url.params.multi_items()) == [("do", "nz"), ("id", provider_id)]
    )


def _allowed_embed(value: str, number: str) -> HttpUrl | None:
    if not value or len(value) > 2048:
        return None
    try:
        url = httpx.URL("https:" + value if value.startswith("//") else value)
    except httpx.InvalidURL as exc:
        raise ParsingError("Malformed source embed URL") from exc
    if url.scheme != "https" or url.port not in (None, 443) or url.userinfo or url.fragment:
        return None
    params = url.params.multi_items()
    if len({key for key, _ in params}) != len(params):
        return None
    if url.host == "rutube.ru":
        valid = re.fullmatch(r"/play/embed/[a-f0-9]{32}/?", url.path) and not params
    elif url.host == "aser.pro":
        valid = re.fullmatch(r"/vod/[1-9][0-9]*", url.path) and not params
    elif url.host == "vk.com":
        valid = (
            url.path == "/video_ext.php"
            and set(url.params) == {"oid", "id", "hash"}
            and re.fullmatch(r"-?[1-9][0-9]*", url.params.get("oid", ""))
            and re.fullmatch(r"[1-9][0-9]*", url.params.get("id", ""))
            and re.fullmatch(r"[a-f0-9]{16}", url.params.get("hash", ""))
        )
    elif url.host == "kodikplayer.com":
        valid = (
            re.fullmatch(r"/serial/[1-9][0-9]*/[a-f0-9]{32}/720p", url.path)
            and set(url.params) == {"season", "episode", "only_translations", "hide_selectors"}
            and re.fullmatch(r"[1-9][0-9]*", url.params.get("season", ""))
            and re.fullmatch(r"[1-9][0-9]*", url.params.get("only_translations", ""))
            and url.params.get("hide_selectors") == "true"
        )
        if valid and url.params.get("episode") != number:
            raise ParsingError("Kodik iframe belongs to a different episode")
    else:
        return None
    return HttpUrl(str(url)) if valid else None


def _frame_url(frame: Tag) -> str:
    urls = [
        value.strip()
        for attr in ("src", "data-src")
        if isinstance(value := frame.get(attr), str) and value.strip()
    ]
    if len(set(urls)) > 1:
        raise ParsingError("Conflicting lazy iframe URL")
    return urls[0] if urls else ""


def parse_player_page(html: bytes, *, episode_id: str) -> WebEmbedPlayerInfo:
    player, links, provider_id, number = _navigation(html, episode_id)
    active = player.select(s.PLAYER_ACTIVE_LINKS)
    if len(active) != len(links) or any(link.get("data-vid") != number for link in active):
        raise ParsingError("AMD selected a different episode")
    for container in player.select(s.EPISODE_LISTS):
        if len(container.select(s.PLAYER_ACTIVE_LINKS)) != 1:
            raise ParsingError("Ambiguous selected episode in navigation copy")

    candidates: list[HttpUrl] = []
    link_values = {str(link.get("data-vlnk", "")).strip() for link in links}
    amedia = player.select(s.PLAYER_AMEDIA_FRAMES)
    frame_values = {_frame_url(frame) for frame in amedia}
    if len(link_values) != 1 or len(frame_values) > 1:
        raise ParsingError("Conflicting Amedia iframe or selected episode links")
    selected = next(iter(link_values))
    if amedia and frame_values != {selected}:
        raise ParsingError("Amedia iframe does not match selected episode")
    if selected and not amedia:
        raise ParsingError("Selected Amedia link has no published iframe")
    try:
        if (
            selected
            and not _placeholder(selected, provider_id)
            and (url := _allowed_embed(selected, number))
        ):
            candidates.append(url)
    except httpx.InvalidURL as exc:
        raise ParsingError("Malformed Amedia iframe URL") from exc

    buttons = player.select(s.PLAYER_KODIK_BUTTONS)
    kodik = player.select(s.PLAYER_KODIK_FRAMES)
    if len(buttons) > 1 or bool(buttons) != bool(kodik):
        raise ParsingError("Missing or ambiguous Kodik tab/iframe")
    if buttons:
        flag = buttons[0].get("data-has-ep")
        values = {_frame_url(frame) for frame in kodik}
        if flag not in ("0", "1") or len(values) != 1:
            raise ParsingError("Conflicting Kodik availability or iframe copies")
        value = values.pop()
        if bool(value) != (flag == "1"):
            raise ParsingError("Kodik availability does not match published iframe")
        if value:
            url = _allowed_embed(value, number)
            if url is not None and url.host != "kodikplayer.com":
                raise ParsingError("Kodik tab points to another embed provider")
            if url is not None:
                candidates.append(url)

    if not candidates:
        raise PlayerUnavailable("No supported public embed for this episode")
    # Prefer documented RUTUBE, then Kodik, then the other observed embed formats.
    order = {"rutube.ru": 0, "kodikplayer.com": 1, "vk.com": 2, "aser.pro": 3}
    chosen = min(candidates, key=lambda url: order[url.host or ""])
    return WebEmbedPlayerInfo(provider="amd", embed_url=chosen)


class AmdPlayerProvider:
    """Resolve public source iframes; never request vendors or extract media URLs."""

    key = "amd"

    def __init__(self, client: httpx.AsyncClient) -> None:
        self.client = client

    async def get_player(self, episode_id: str) -> WebEmbedPlayerInfo:
        if not episode_id.startswith("amd:") and ":" in episode_id:
            raise NotFound("Unknown player provider namespace")
        provider_id, number = episode_identity(episode_id)
        detail, _ = await fetch_detail_html(self.client, provider_id)
        url = await asyncio.to_thread(episode_page_url, detail, episode_id=episode_id)
        body = await fetch_episode_html(self.client, url, provider_id, number)
        return await asyncio.to_thread(parse_player_page, body, episode_id=episode_id)

    async def supports_embed(self, episode_id: str) -> bool:
        return await self.get_embed_url(episode_id) is not None

    async def get_embed_url(self, episode_id: str) -> HttpUrl | None:
        try:
            return (await self.get_player(episode_id)).embed_url
        except PlayerUnavailable:
            return None
