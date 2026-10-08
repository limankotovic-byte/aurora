from datetime import UTC, datetime

import pytest
from pydantic import TypeAdapter, ValidationError

from app.models.anime import Anime, AnimeStatus
from app.models.catalog import HomeCatalog, Pagination, SearchQuery
from app.models.episode import Episode
from app.models.player import PlayerInfo, WebEmbedPlayerInfo
from app.models.release import Release


def anime_data() -> dict[str, object]:
    return {"id": "test:anime-1", "provider": "test", "provider_id": "1", "title": "  Аврора  "}


def test_missing_metadata_is_unknown_not_fabricated() -> None:
    anime = Anime.model_validate(anime_data())
    assert anime.title == "Аврора"
    assert anime.rating is None
    assert anime.year is None
    assert anime.updated_at is None
    assert anime.status == AnimeStatus.UNKNOWN
    assert anime.genres == []
    episode = Episode(id="test:episode-1", anime_id=anime.id)
    assert not episode.available
    assert episode.number is None
    assert episode.player_id is None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("title", "   "),
        ("id", "raw/path/1"),
        ("id", "other:anime-1"),
        ("rating", 10.1),
        ("rating", -1),
        ("rating", float("nan")),
        ("episode_count", -1),
        ("poster_url", "javascript:alert(1)"),
        ("updated_at", "2026-10-07T12:00:00"),
        ("raw_html", "unexpected-provider-data"),
    ],
)
def test_invalid_normalized_anime_is_rejected(field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        Anime.model_validate(anime_data() | {field: value})


def test_timestamps_normalize_to_utc() -> None:
    anime = Anime.model_validate(anime_data() | {"updated_at": "2026-10-07T12:00:00+03:00"})
    assert anime.updated_at == datetime(2026, 10, 7, 9, tzinfo=UTC)
    assert anime.model_dump(mode="json")["updated_at"] == "2026-10-07T09:00:00Z"


def test_release_cannot_reference_another_anime() -> None:
    anime = Anime.model_validate(anime_data())
    episode = Episode(id="test:episode-2", anime_id="test:anime-2")
    with pytest.raises(ValidationError, match="belong"):
        Release(anime=anime, episode=episode, provider="test")


def test_collection_defaults_are_not_shared() -> None:
    first, second = HomeCatalog(), HomeCatalog()
    first.featured.append(Anime.model_validate(anime_data()))
    assert second.featured == []


@pytest.mark.parametrize(("field", "value"), [("page", 0), ("page_size", 0), ("page_size", 51)])
def test_pagination_bounds(field: str, value: int) -> None:
    with pytest.raises(ValidationError):
        Pagination.model_validate({field: value})


def test_search_trims_and_rejects_empty_or_oversized_queries() -> None:
    assert SearchQuery(q="  Аврора  ").q == "Аврора"
    for query in ("  ", "a" * 201):
        with pytest.raises(ValidationError):
            SearchQuery(q=query)


@pytest.mark.parametrize(
    ("kind", "field"),
    [("WEB_EMBED", "embed_url"), ("NATIVE_STREAM", "stream_url"), ("EXTERNAL", "external_url")],
)
def test_player_variants_require_their_own_url(kind: str, field: str) -> None:
    adapter = TypeAdapter[PlayerInfo](PlayerInfo)
    player = adapter.validate_python(
        {"type": kind, "provider": "test", field: "https://player.example/public"}
    )
    assert player.type == kind
    with pytest.raises(ValidationError):
        adapter.validate_python({"type": kind, "provider": "test"})


def test_embed_rejects_unsafe_and_conflicting_fields() -> None:
    for extra in (
        {"embed_url": "file:///etc/passwd"},
        {"embed_url": "https://player.example/public", "stream_url": "https://example.com/v"},
    ):
        with pytest.raises(ValidationError):
            WebEmbedPlayerInfo.model_validate({"provider": "test"} | extra)


def test_player_capabilities_default_is_conservative_and_isolated() -> None:
    first = WebEmbedPlayerInfo.model_validate(
        {"provider": "test", "embed_url": "https://player.example/public"}
    )
    second = WebEmbedPlayerInfo.model_validate(
        {"provider": "test", "embed_url": "https://player.example/public"}
    )
    assert first.capabilities.model_dump() == {
        "progress": False,
        "seek": False,
        "fullscreen": False,
    }
    first.capabilities.seek = True
    assert not second.capabilities.seek
