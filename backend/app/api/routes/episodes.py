from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from app.api.dependencies import get_anime_provider
from app.models.base import EntityId
from app.models.catalog import Pagination
from app.providers.base import AnimeProvider
from app.schemas.common import ErrorResponse
from app.schemas.episodes import EpisodePageResponse, EpisodeParams, EpisodeResponse
from app.services.episodes import EpisodeService

router = APIRouter(tags=["episodes"])


@router.get(
    "/anime/{id}/episodes",
    response_model=EpisodePageResponse,
    responses={code: {"model": ErrorResponse} for code in (404, 422, 429, 500, 502, 503)},
)
async def anime_episodes(
    anime_id: Annotated[EntityId, Path(alias="id")],
    params: Annotated[EpisodeParams, Query()],
    provider: Annotated[AnimeProvider, Depends(get_anime_provider)],
) -> EpisodePageResponse:
    result = await EpisodeService(provider).get_episodes(
        anime_id, Pagination(page=params.page, page_size=params.page_size), season=params.season
    )
    return EpisodePageResponse(
        items=[EpisodeResponse.from_domain(episode) for episode in result.items],
        page=result.page,
        page_size=result.page_size,
        has_next=result.has_next,
        total=result.total,
    )
