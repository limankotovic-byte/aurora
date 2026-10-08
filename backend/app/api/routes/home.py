from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_anime_provider
from app.models.catalog import Pagination
from app.providers.base import AnimeProvider
from app.schemas.common import ErrorResponse
from app.schemas.home import HomeResponse, ReleasePageResponse, ReleaseParams, ReleaseResponse

router = APIRouter(tags=["home"], responses={c: {"model": ErrorResponse} for c in (429, 502, 503)})


@router.get("/home", response_model=HomeResponse)
async def home(provider: Annotated[AnimeProvider, Depends(get_anime_provider)]) -> HomeResponse:
    catalog = await provider.get_home()
    return HomeResponse.model_validate(catalog.model_dump() | {"continue_watching": []})


@router.get(
    "/releases/latest",
    response_model=ReleasePageResponse,
    responses={422: {"model": ErrorResponse}},
)
async def releases(
    params: Annotated[ReleaseParams, Query()],
    provider: Annotated[AnimeProvider, Depends(get_anime_provider)],
) -> ReleasePageResponse:
    result = await provider.get_latest_releases(
        Pagination.model_validate(params.model_dump(by_alias=False))
    )
    return ReleasePageResponse(
        items=[ReleaseResponse.from_domain(r) for r in result.items],
        page=result.page,
        page_size=result.page_size,
        has_next=result.has_next,
        total=result.total,
    )
