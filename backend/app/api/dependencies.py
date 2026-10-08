from dataclasses import dataclass
from typing import Annotated, cast

import httpx
from fastapi import Depends, Request

from app.core.config import Settings
from app.core.exceptions import PlayerUnavailable, ProviderUnavailable
from app.providers.base import AnimeProvider, PlayerProvider


@dataclass(frozen=True)
class AppResources:
    settings: Settings
    http_client: httpx.AsyncClient
    anime_provider: AnimeProvider | None = None
    player_provider: PlayerProvider | None = None


def get_resources(request: Request) -> AppResources:
    return cast(AppResources, request.app.state.resources)


type ResourcesDependency = Annotated[AppResources, Depends(get_resources)]


def get_anime_provider(resources: ResourcesDependency) -> AnimeProvider:
    if resources.anime_provider is None:
        raise ProviderUnavailable("No catalog provider configured")
    return resources.anime_provider


def get_player_provider(resources: ResourcesDependency) -> PlayerProvider:
    if resources.player_provider is None:
        raise PlayerUnavailable("No player provider configured")
    return resources.player_provider
