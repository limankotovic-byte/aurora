import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag
from pydantic import HttpUrl, ValidationError

from app.core.exceptions import ParsingError
from app.providers.amd import selectors
from app.providers.amd.models import ParsedAnimeDetails


def _text(element: Tag | None) -> str:
    if element is None:
        return ""
    return " ".join(element.get_text(" ", strip=True).split())


def _http_url(value: str, base: HttpUrl) -> HttpUrl | None:
    if not value.strip():
        return None
    try:
        url = HttpUrl(urljoin(str(base), value.strip()))
    except (ValidationError, ValueError):
        return None
    if url.username is not None or url.password is not None:
        return None
    return url


def _catalog_path(link: Tag, base: HttpUrl) -> str | None:
    href = link.get("href")
    if not isinstance(href, str):
        return None
    url = _http_url(href, base)
    if url is None or url.host != base.host:
        return None
    return url.path


def _poster(root: Tag, base: HttpUrl) -> HttpUrl | None:
    image = root.select_one(selectors.POSTER)
    if image is None:
        return None
    src = image.get("src")
    return _http_url(src, base) if isinstance(src, str) else None


def _description(root: Tag) -> str | None:
    element = root.select_one(selectors.DESCRIPTION)
    if element is None:
        return None
    paragraphs = [
        _text(paragraph) for paragraph in element.select(selectors.DESCRIPTION_PARAGRAPHS)
    ]
    if paragraphs:
        return "\n\n".join(paragraph for paragraph in paragraphs if paragraph) or None
    return _text(element) or None


def _genres(root: Tag, base: HttpUrl) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for link in root.select(selectors.GENRE_LINKS):
        path = _catalog_path(link, base)
        if path is None or not path.startswith(selectors.GENRE_PATH_PREFIX):
            continue
        genre = _text(link)
        if genre and genre.casefold() not in seen:
            result.append(genre)
            seen.add(genre.casefold())
    return result


def _year(root: Tag, base: HttpUrl) -> int | None:
    years: set[int] = set()
    for link in root.select(selectors.YEAR_LINKS):
        path = _catalog_path(link, base)
        match = re.fullmatch(selectors.YEAR_PATH_PATTERN, path or "")
        if match is None:
            continue
        year = int(match["year"])
        # Both visible text and the dedicated year link must agree.
        if year > 0 and _text(link) == match["year"]:
            years.add(year)
    return next(iter(years)) if len(years) == 1 else None


def parse_anime_page(html: str | bytes, *, page_url: str) -> ParsedAnimeDetails:
    """Parse an already-fetched public details page without I/O or script execution.

    A missing/ambiguous detail card or empty title raises ParsingError. Missing or
    unusable optional fields remain None/[], rather than borrowing unrelated page
    content. The caller supplies the final page URL for relative poster URLs.
    """
    try:
        base = HttpUrl(page_url)
    except ValidationError as exc:
        raise ParsingError("AMD parser requires an absolute HTTP(S) page URL") from exc
    if base.username is not None or base.password is not None:
        raise ParsingError("AMD page URL must not contain credentials")

    soup = BeautifulSoup(html, "html.parser")
    for element in soup.select(selectors.NON_CONTENT):
        element.decompose()
    roots = soup.select(selectors.DETAILS_ROOT)
    if len(roots) != 1:
        raise ParsingError("Expected exactly one AMD details card")
    root = roots[0]
    title = _text(root.select_one(selectors.TITLE))
    if not title:
        raise ParsingError("AMD details title is missing or empty")

    return ParsedAnimeDetails(
        title=title,
        poster_url=_poster(root, base),
        description=_description(root),
        genres=_genres(root, base),
        year=_year(root, base),
    )
