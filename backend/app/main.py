from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from app.api.dependencies import AppResources
from app.api.errors import register_error_handlers
from app.api.routes.anime import router as anime_router
from app.api.routes.episodes import router as episodes_router
from app.api.routes.health import router as health_router
from app.api.routes.home import router as home_router
from app.api.routes.search import router as search_router
from app.core.config import Settings
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware
from app.providers.amd.provider import AmdProvider
from app.providers.base import AnimeProvider, PlayerProvider
from app.services.cache import CacheService
from app.services.cached_provider import CachedAnimeProvider


def create_app(
    settings: Settings | None = None,
    *,
    anime_provider: AnimeProvider | None = None,
    player_provider: PlayerProvider | None = None,
) -> FastAPI:
    config = settings if settings is not None else Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
        configure_logging(config.log_level)
        async with httpx.AsyncClient(
            timeout=config.http_timeout_seconds,
            limits=httpx.Limits(
                max_connections=config.http_max_connections,
                max_keepalive_connections=config.http_max_keepalive_connections,
            ),
            follow_redirects=False,
        ) as http_client:
            catalog = anime_provider
            if catalog is None and config.catalog_provider == "amd":
                catalog = AmdProvider(http_client)
            cache = CacheService()
            if catalog is not None:
                catalog = CachedAnimeProvider(catalog, cache)
            app.state.resources = AppResources(
                settings=config,
                http_client=http_client,
                anime_provider=catalog,
                player_provider=player_provider,
            )
            try:
                yield
            finally:
                await cache.close()
                del app.state.resources

    app = FastAPI(
        title="Aurora API",
        version="0.1.0",
        lifespan=lifespan,
        debug=False,
    )
    app.add_middleware(RequestContextMiddleware)
    register_error_handlers(app)
    app.include_router(health_router)
    app.include_router(anime_router)
    app.include_router(episodes_router)
    app.include_router(search_router)
    app.include_router(home_router)
    return app
