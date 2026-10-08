from typing import Annotated

from fastapi import APIRouter, Depends, Path

from app.api.dependencies import get_anime_provider
from app.models.base import EntityId
from app.providers.base import AnimeProvider
from app.schemas.anime import AnimeResponse
from app.schemas.common import ErrorResponse
from app.services.catalog import CatalogService

router = APIRouter(tags=["anime"])


@router.get(
    "/anime/{id}",
    response_model=AnimeResponse,
    responses={code: {"model": ErrorResponse} for code in (404, 422, 429, 500, 502, 503)},
)
async def anime_details(
    anime_id: Annotated[EntityId, Path(alias="id")],
    provider: Annotated[AnimeProvider, Depends(get_anime_provider)],
) -> AnimeResponse:
    return AnimeResponse.from_domain(await CatalogService(provider).get_anime(anime_id))
