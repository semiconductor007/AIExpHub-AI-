"""Object-only JSON Pointer mappings; no experiment data is stored here."""

import re
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

TemplateName = Annotated[str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=100)]


class MappingInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    metric_key: Annotated[str, StringConstraints(strict=True, min_length=1, max_length=64)]
    metric_id: Annotated[int, Field(strict=True, gt=0)] | None = None
    builtin: Annotated[bool, Field(strict=True)]
    pointer: Annotated[str, StringConstraints(strict=True, min_length=1, max_length=4096)]

    @field_validator("pointer")
    @classmethod
    def object_pointer(cls, value: str) -> str:
        if not value.startswith("/") or re.search(r"~(?![01])", value) or len(value.split("/")) > 101:
            raise ValueError("映射路径必须为合法 JSON Pointer，且最多 100 层")
        return value


class TemplateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: TemplateName
    mappings: list[MappingInput] = Field(min_length=1, max_length=500, strict=True)

    @field_validator("mappings")
    @classmethod
    def distinct_metrics(cls, value: list[MappingInput]) -> list[MappingInput]:
        if len({item.metric_key for item in value}) != len(value):
            raise ValueError("同一个模板不能重复映射相同指标")
        return value


class TemplateRename(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: TemplateName


class MappingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    metric_key: str
    metric_id: int | None
    builtin: bool
    pointer: str


class TemplateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    name: str
    mappings: list[MappingRead]
