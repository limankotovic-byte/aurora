from typing import Literal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from app.core.exceptions import ErrorCode


class ApiModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        validate_by_name=True,
        serialize_by_alias=True,
        extra="forbid",
    )


class HealthResponse(ApiModel):
    status: Literal["ok"] = "ok"


class ErrorDetail(ApiModel):
    code: ErrorCode
    message: str
    request_id: str


class ErrorResponse(ApiModel):
    error: ErrorDetail
