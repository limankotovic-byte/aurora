from datetime import UTC, datetime
from typing import Annotated

from pydantic import AfterValidator, AwareDatetime, BaseModel, ConfigDict, StringConstraints

type NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
type ProviderKey = Annotated[
    str, StringConstraints(pattern=r"^[a-z][a-z0-9_-]*$", min_length=1, max_length=64)
]
type EntityId = Annotated[
    str,
    StringConstraints(pattern=r"^[a-z][a-z0-9_-]*:[A-Za-z0-9._~-]+$", max_length=512),
]


def _as_utc(value: datetime) -> datetime:
    return value.astimezone(UTC)


type UtcDatetime = Annotated[AwareDatetime, AfterValidator(_as_utc)]


class DomainModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, validate_default=True)
