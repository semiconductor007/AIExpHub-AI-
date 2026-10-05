"""Request and response schemas for projects and experiment batches."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints


Name = Annotated[
    str, StringConstraints(strict=True, strip_whitespace=True, min_length=1)
]


class _NamedResourceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Name
    description: str | None = None


class ProjectCreate(_NamedResourceInput):
    pass


class ProjectUpdate(_NamedResourceInput):
    pass


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    created_at: datetime


class BatchCreate(_NamedResourceInput):
    pass


class BatchUpdate(_NamedResourceInput):
    pass


class BatchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    name: str
    description: str | None
    created_at: datetime
