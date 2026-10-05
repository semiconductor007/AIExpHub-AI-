"""Request and response schemas for projects, batches and experiments."""

from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator


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


class _ExperimentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    experiment_no: Name
    model_name: Name
    parameters: dict[str, Any] = Field(strict=True)
    notes: str | None = None

    @field_validator("experiment_no")
    @classmethod
    def normalize_experiment_no(cls, value: str) -> str:
        # Name already enforces strict strings, trim and nonblank input.
        return value.upper()

    @field_validator("parameters")
    @classmethod
    def require_nonempty_parameters(cls, value: dict[str, Any]) -> dict[str, Any]:
        if not value:
            raise ValueError("parameters must be a non-empty JSON object")
        return value


class ExperimentCreate(_ExperimentInput):
    pass


class ExperimentUpdate(_ExperimentInput):
    pass


class ExperimentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    batch_id: int
    experiment_no: str
    model_name: str
    parameters: dict[str, Any]
    created_at: datetime
    notes: str | None
