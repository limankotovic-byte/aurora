from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_anime_provider
from app.models.catalog import SearchQuery
from app.providers.base import AnimeProvider
from app.schemas.anime import AnimeResponse
from app.schemas.common import ErrorResponse
from app.schemas.search import SearchParams, SearchResponse
from app.services.search import SearchService

router = APIRouter(tags=["search"])


@router.get(
    "/search",
    response_model=SearchResponse,
    responses={code: {"model": ErrorResponse} for code in (422, 429, 502, 503)},
)
async def search_anime(
    params: Annotated[SearchParams, Query()],
    provider: Annotated[AnimeProvider, Depends(get_anime_provider)],
) -> SearchResponse:
    query = SearchQuery.model_validate(params.model_dump(by_alias=False))
    result = await SearchService(provider).search(query)
    return SearchResponse(
        items=[AnimeResponse.from_domain(item) for item in result.items],
        page=result.page,
        page_size=result.page_size,
        has_next=result.has_next,
        total=result.total,
    )
