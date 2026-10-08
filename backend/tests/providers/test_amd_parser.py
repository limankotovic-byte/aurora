from pathlib import Path

import pytest
from bs4 import BeautifulSoup, Tag

from app.core.exceptions import ParsingError
from app.providers.amd import selectors
from app.providers.amd.parser import parse_anime_page

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "amd_anime.html"
PAGE_URL = "https://amd.online/1489-protivostojanie-svjatogo.html"


@pytest.fixture
def html() -> str:
    return FIXTURE.read_text(encoding="utf-8")


def required(soup: BeautifulSoup, selector: str) -> Tag:
    element = soup.select_one(selector)
    assert element is not None, f"Fixture element not found: {selector}"
    return element


def test_real_fixture_extracts_only_the_five_metadata_fields(html: str) -> None:
    result = parse_anime_page(html, page_url=PAGE_URL)
    assert result.title == "Противостояние святого"
    assert str(result.poster_url) == "https://amd.online/uploads/posts/2024-12/original.webp"
    assert result.genres == ["экшен", "приключения", "фэнтези", "исторический", "китайское", "3D"]
    assert result.year == 2023
    assert result.description is not None
    assert result.description.startswith("Ван Линь - молодой человек из деревни,")
    assert "\n\nВан Линь решает воспользоваться этой возможностью," in result.description
    assert result.description.endswith("и самостоятельно написать свою судьбу.")
    assert set(result.model_dump()) == {"title", "poster_url", "description", "genres", "year"}


def test_utf8_bytes_preserve_cyrillic(html: str) -> None:
    assert parse_anime_page(html.encode(), page_url=PAGE_URL) == parse_anime_page(
        html, page_url=PAGE_URL
    )


@pytest.mark.parametrize(
    "markup",
    ["", "<html><h1>Access denied</h1></html>", '<div class="amd-card"><h1>Wrong page</h1></div>'],
)
def test_non_details_pages_raise_parsing_error(markup: str) -> None:
    with pytest.raises(ParsingError, match="details card"):
        parse_anime_page(markup, page_url=PAGE_URL)


def test_ambiguous_detail_cards_are_not_silently_chosen(html: str) -> None:
    with pytest.raises(ParsingError, match="exactly one"):
        parse_anime_page(html + html, page_url=PAGE_URL)


@pytest.mark.parametrize("missing", [True, False])
def test_title_is_required_even_with_document_title(html: str, missing: bool) -> None:
    soup = BeautifulSoup(html, "html.parser")
    title = required(soup, selectors.TITLE)
    if missing:
        title.decompose()
    else:
        title.string = " \n\t "
    with pytest.raises(ParsingError, match="title"):
        parse_anime_page(str(soup), page_url=PAGE_URL)


def test_changed_mandatory_selector_is_an_error(html: str) -> None:
    with pytest.raises(ParsingError):
        parse_anime_page(html.replace('class="amd-title"', 'class="new-title"'), page_url=PAGE_URL)


def test_absent_optional_metadata_remains_unknown(html: str) -> None:
    soup = BeautifulSoup(html, "html.parser")
    for selector in (
        selectors.POSTER,
        selectors.DESCRIPTION,
        selectors.GENRE_LINKS,
        selectors.YEAR_LINKS,
    ):
        for node in soup.select(selector):
            node.decompose()
    result = parse_anime_page(str(soup), page_url=PAGE_URL)
    assert result.title == "Противостояние святого"
    assert result.poster_url is None  # The nested clan avatar is not a fallback poster.
    assert result.description is None
    assert result.genres == []  # The page header contains an unrelated genre.
    assert result.year is None


@pytest.mark.parametrize(
    ("src", "expected"),
    [
        ("/uploads/poster.webp", "https://amd.online/uploads/poster.webp"),
        ("poster.webp", "https://amd.online/poster.webp"),
        ("//cdn.example/poster.webp", "https://cdn.example/poster.webp"),
        ("https://cdn.example/poster.webp", "https://cdn.example/poster.webp"),
        ("", None),
        ("   ", None),
        ("javascript:alert(1)", None),
        ("data:image/png;base64,AAA", None),
        ("file:///tmp/poster.webp", None),
        ("https://user:password@cdn.example/poster.webp", None),
        ("https://[broken/poster.webp", None),
    ],
)
def test_poster_url_normalization(html: str, src: str, expected: str | None) -> None:
    soup = BeautifulSoup(html, "html.parser")
    required(soup, selectors.POSTER)["src"] = src
    result = parse_anime_page(str(soup), page_url=PAGE_URL)
    assert (str(result.poster_url) if result.poster_url else None) == expected


def test_genres_deduplicate_without_collecting_foreign_or_collection_links(html: str) -> None:
    soup = BeautifulSoup(html, "html.parser")
    link = required(soup, selectors.GENRE_LINKS)
    duplicate = soup.new_tag("a", href="/anime/ghanr/other-spelling/")
    duplicate.string = "  ЭКШЕН  "
    link.insert_after(duplicate)
    foreign = soup.new_tag("a", href="https://other.example/anime/ghanr/other/")
    foreign.string = "Чужой жанр"
    link.insert_after(foreign)
    result = parse_anime_page(str(soup), page_url=PAGE_URL)
    assert result.genres == ["экшен", "приключения", "фэнтези", "исторический", "китайское", "3D"]


@pytest.mark.parametrize("label", ["неизвестно", "2023–2024", "2024", "0000", ""])
def test_invalid_or_mismatched_year_is_not_guessed(html: str, label: str) -> None:
    soup = BeautifulSoup(html, "html.parser")
    required(soup, selectors.YEAR_LINKS).string = label
    assert parse_anime_page(str(soup), page_url=PAGE_URL).year is None


def test_missing_year_link_does_not_use_season_year(html: str) -> None:
    soup = BeautifulSoup(html, "html.parser")
    required(soup, selectors.YEAR_LINKS).decompose()
    assert parse_anime_page(str(soup), page_url=PAGE_URL).year is None


def test_conflicting_valid_years_are_unknown(html: str) -> None:
    soup = BeautifulSoup(html, "html.parser")
    year = required(soup, selectors.YEAR_LINKS)
    other = soup.new_tag("a", href="/anime/god/2024/")
    other.string = "2024"
    year.insert_after(other)
    assert parse_anime_page(str(soup), page_url=PAGE_URL).year is None


def test_text_normalization_and_non_content_exclusion(html: str) -> None:
    soup = BeautifulSoup(html, "html.parser")
    title = required(soup, selectors.TITLE)
    title.string = "  Название\n\t с\xa0пробелами  "
    description = required(soup, selectors.DESCRIPTION)
    description.clear()
    description.append(
        BeautifulSoup(
            "<p> Первый &amp; <strong>второй</strong> </p><p>Третий.</p>"
            '<script>throw new Error("not metadata")</script><style>bad-css</style>'
            "<template><p>hidden-template</p></template><noscript>hidden-noscript</noscript>",
            "html.parser",
        )
    )
    result = parse_anime_page(str(soup), page_url=PAGE_URL)
    assert result.title == "Название с пробелами"
    assert result.description == "Первый & второй\n\nТретий."


@pytest.mark.parametrize(("text", "expected"), [(" Plain\n text ", "Plain text"), (" \n ", None)])
def test_description_without_paragraph_tags(html: str, text: str, expected: str | None) -> None:
    soup = BeautifulSoup(html, "html.parser")
    required(soup, selectors.DESCRIPTION).string = text
    assert parse_anime_page(str(soup), page_url=PAGE_URL).description == expected


@pytest.mark.parametrize(
    "url", ["/relative", "file:///tmp/page.html", "https://user:pw@amd.online/"]
)
def test_invalid_base_url_is_a_parsing_error(html: str, url: str) -> None:
    with pytest.raises(ParsingError, match="URL"):
        parse_anime_page(html, page_url=url)
