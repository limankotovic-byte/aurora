import re

import httpx

from app.core.exceptions import InvalidAnimeId, InvalidEpisodeId, ProviderUnavailable

ORIGIN = "https://amd.online"
ID_PATTERN = r"amd:([1-9][0-9]{0,11})"
DETAIL_PATH_PATTERN = r"/([1-9][0-9]{0,11})-[^/]+\.html"
EPISODE_NUMBER_PATTERN = r"[1-9][0-9]{0,6}"
EPISODE_PATH_PATTERN = (
    rf"/([1-9][0-9]{{0,11}})-[^/]+/episode/({EPISODE_NUMBER_PATTERN})/seriya-onlayn\.html"
)


def episode_id(provider_id: str, number: str) -> str:
    return f"amd:{provider_id}-episode-{number}"


def episode_identity(value: str) -> tuple[str, str]:
    match = re.fullmatch(rf"amd:([1-9][0-9]{{0,11}})-episode-({EPISODE_NUMBER_PATTERN})", value)
    if match is None:
        raise InvalidEpisodeId()
    return match[1], match[2]


def validate_episode_url(url: httpx.URL, provider_id: str, number: str) -> None:
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
        raise ProviderUnavailable("Unexpected AMD episode redirect or identity")


def source_id(anime_id: str) -> str:
    match = re.fullmatch(ID_PATTERN, anime_id)
    if match is None:
        raise InvalidAnimeId()
    return match[1]


def lookup_url(provider_id: str) -> httpx.URL:
    return httpx.URL(f"{ORIGIN}/index.php", params={"newsid": provider_id})


def validate_detail_url(url: httpx.URL, provider_id: str) -> None:
    match = re.fullmatch(DETAIL_PATH_PATTERN, url.path)
    if (
        url.scheme != "https"
        or url.host != "amd.online"
        or url.port not in (None, 443)
        or url.userinfo
        or url.query
        or match is None
        or match[1] != provider_id
    ):
        raise ProviderUnavailable("Unexpected AMD detail redirect or identity")
