from typing import Literal, Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AURORA_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
        allow_inf_nan=False,
    )

    environment: Literal["development", "test", "production"] = "development"
    catalog_provider: Literal["amd", "none"] = "amd"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    http_timeout_seconds: float = Field(default=10, gt=0, le=120)
    http_max_connections: int = Field(default=20, ge=1, le=100)
    http_max_keepalive_connections: int = Field(default=10, ge=0, le=100)

    @model_validator(mode="after")
    def validate_connection_limits(self) -> Self:
        if self.http_max_keepalive_connections > self.http_max_connections:
            raise ValueError("Keepalive connections cannot exceed total connections")
        return self
