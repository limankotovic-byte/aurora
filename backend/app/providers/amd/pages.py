import httpx

from app.core.exceptions import (
    NetworkError,
    NotFound,
    ParsingError,
    ProviderUnavailable,
    RateLimited,
)
from app.providers.amd.identity import lookup_url, validate_detail_url, validate_episode_url

MAX_HTML_BYTES = 2 * 1024 * 1024
MAX_REDIRECTS = 3


async def _fetch(
    client: httpx.AsyncClient, url: httpx.URL, provider_id: str, number: str | None = None
) -> tuple[bytes, str]:
    def validate(target: httpx.URL) -> None:
        if number is None:
            validate_detail_url(target, provider_id)
        else:
            validate_episode_url(target, provider_id, number)

    try:
        for hop in range(MAX_REDIRECTS + 1):
            if number is not None or hop > 0:
                validate(url)
            async with client.stream("GET", url, follow_redirects=False) as response:
                if response.status_code in (404, 410):
                    raise NotFound()
                if response.status_code == 429:
                    retry = response.headers.get("retry-after", "")
                    seconds = int(retry) if retry.isascii() and retry.isdigit() else None
                    raise RateLimited(retry_after=seconds)
                if response.status_code in (301, 302, 303, 307, 308):
                    location = response.headers.get("location")
                    if not location or hop == MAX_REDIRECTS:
                        raise ProviderUnavailable("Invalid AMD redirect chain")
                    url = response.url.join(location)
                    validate(url)
                    continue
                if response.status_code != 200:
                    raise ProviderUnavailable("AMD returned an unsuccessful response")
                validate(response.url)
                media_type = response.headers.get("content-type", "").split(";")[0].strip()
                if media_type.lower() != "text/html":
                    raise ParsingError("Expected AMD HTML response")
                body = bytearray()
                async for chunk in response.aiter_bytes(chunk_size=65536):
                    body.extend(chunk)
                    if len(body) > MAX_HTML_BYTES:
                        raise ParsingError("AMD response exceeds metadata size limit")
                return bytes(body), str(response.url)
    except httpx.InvalidURL as exc:
        raise ProviderUnavailable("Malformed AMD page URL") from exc
    except httpx.RequestError as exc:
        raise NetworkError("AMD transport failed") from exc
    raise ProviderUnavailable("AMD redirect limit exceeded")


async def fetch_detail_html(client: httpx.AsyncClient, provider_id: str) -> tuple[bytes, str]:
    return await _fetch(client, lookup_url(provider_id), provider_id)


async def fetch_episode_html(
    client: httpx.AsyncClient, url: httpx.URL, provider_id: str, number: str
) -> bytes:
    body, _ = await _fetch(client, url, provider_id, number)
    return body
