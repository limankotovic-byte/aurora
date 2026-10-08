from app.models.catalog import SearchQuery
from app.schemas.anime import AnimeResponse
from app.schemas.common import ApiModel


class SearchParams(SearchQuery, ApiModel):
    """Validated query parameters with camelCase pageSize and forbidden extras."""


class SearchResponse(ApiModel):
    items: list[AnimeResponse]
    page: int
    page_size: int
    has_next: bool
    total: int | None
