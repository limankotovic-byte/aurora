from typing import Annotated, Literal

from pydantic import Field, HttpUrl

from app.models.base import DomainModel, NonEmptyString, ProviderKey


class PlayerBase(DomainModel):
    provider: ProviderKey
    quality_hint: NonEmptyString | None = None


class PlayerCapabilities(DomainModel):
    """Features enabled in Aurora, not merely documented by a third-party vendor."""

    progress: bool = False
    seek: bool = False
    fullscreen: bool = False


class WebEmbedPlayerInfo(PlayerBase):
    type: Literal["WEB_EMBED"] = "WEB_EMBED"
    embed_url: HttpUrl
    capabilities: PlayerCapabilities = Field(default_factory=PlayerCapabilities)


class NativeStreamPlayerInfo(PlayerBase):
    type: Literal["NATIVE_STREAM"] = "NATIVE_STREAM"
    stream_url: HttpUrl


class ExternalPlayerInfo(PlayerBase):
    type: Literal["EXTERNAL"] = "EXTERNAL"
    external_url: HttpUrl


type PlayerInfo = Annotated[
    WebEmbedPlayerInfo | NativeStreamPlayerInfo | ExternalPlayerInfo,
    Field(discriminator="type"),
]
