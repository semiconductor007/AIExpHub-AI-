"""Strict choices and evidence-bound narrative, separate from business schemas."""

from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StringConstraints, model_validator

PositiveId = Annotated[StrictInt, Field(gt=0)]
ShortText = Annotated[str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=600)]
Reference = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=1024)]
SECTIONS = ("overview", "metrics", "parameters", "limitations", "next_steps")


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class SummarySelection(StrictModel):
    experiment_ids: list[PositiveId] = Field(min_length=2, max_length=10)
    baseline_experiment_id: PositiveId | None = None
    primary_metric: Reference | None = None
    parameter_paths: list[Reference] = Field(default_factory=list, max_length=128)

    @model_validator(mode="after")
    def distinct_choices(self) -> Self:
        if len(set(self.experiment_ids)) != len(self.experiment_ids):
            raise ValueError("请选择至少两个不同实验，不能重复选择")
        if self.baseline_experiment_id is not None and self.baseline_experiment_id not in self.experiment_ids:
            raise ValueError("基准实验必须属于当前选择")
        if len(set(self.parameter_paths)) != len(self.parameter_paths):
            raise ValueError("参数路径不能重复")
        return self


class SnapshotCheck(SummarySelection):
    fingerprint: Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{64}$")]


class GenerateSummary(SnapshotCheck):
    request_id: UUID


class ProviderItem(StrictModel):
    kind: Literal["observation", "hypothesis", "suggestion"]
    text: ShortText
    evidence_ids: list[Reference] = Field(min_length=1, max_length=32)


class NarrativeItem(ProviderItem):
    experiment_ids: list[PositiveId] = Field(max_length=10)
    metric_ids: list[Reference] = Field(max_length=64)


class ProviderSection(StrictModel):
    key: Literal["overview", "metrics", "parameters", "limitations", "next_steps"]
    items: list[ProviderItem] = Field(min_length=1, max_length=4)


class NarrativeSection(ProviderSection):
    items: list[NarrativeItem] = Field(min_length=1, max_length=4)


class ProviderNarrative(StrictModel):
    sections: list[ProviderSection] = Field(min_length=5, max_length=5)

    @model_validator(mode="after")
    def fixed_sections(self) -> Self:
        if tuple(section.key for section in self.sections) != SECTIONS:
            raise ValueError("总结章节缺失、重复或顺序不符")
        return self


class SummaryNarrative(ProviderNarrative):
    sections: list[NarrativeSection] = Field(min_length=5, max_length=5)
