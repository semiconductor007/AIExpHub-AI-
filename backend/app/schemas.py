"""Request and response schemas for experiments, results and comparison."""

from datetime import datetime
from typing import Annotated, Any, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)


Name = Annotated[
    str, StringConstraints(strict=True, strip_whitespace=True, min_length=1)
]
FiniteMetric = Annotated[float, Field(strict=True, allow_inf_nan=False)]
MetricKey = Annotated[str, StringConstraints(strict=True, pattern=r"^[a-z][a-z0-9_]{0,63}$")]


class ProjectMetricInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: MetricKey
    name: Name
    unit: Annotated[str, StringConstraints(strict=True, strip_whitespace=True)] = ""
    direction: Literal["max", "min"]
    lower_bound: FiniteMetric | None = None
    upper_bound: FiniteMetric | None = None

    @field_validator("key", mode="before")
    @classmethod
    def normalize_key(cls, value: Any) -> Any:
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator("key")
    @classmethod
    def reserve_keys(cls, value: str) -> str:
        if value in {"accuracy", "precision", "recall", "f1", "loss", "custom_metrics", "id", "experiment_id", "updated_at", "constructor", "prototype"}:
            raise ValueError("指标键与系统字段冲突，请换一个键名")
        return value

    @model_validator(mode="after")
    def ordered_bounds(self) -> Self:
        if self.lower_bound is not None and self.upper_bound is not None and self.lower_bound > self.upper_bound:
            raise ValueError("指标下限不能大于上限")
        return self


class ProjectMetricRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    project_id: int
    key: str
    name: str
    unit: str
    direction: Literal["max", "min"]
    lower_bound: float | None
    upper_bound: float | None
    builtin: bool = False


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


class _ExperimentResultInput(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    accuracy: float | None = Field(default=None, ge=0, le=1)
    precision: float | None = Field(default=None, ge=0, le=1)
    recall: float | None = Field(default=None, ge=0, le=1)
    f1: float | None = Field(default=None, ge=0, le=1)
    loss: float | None = Field(default=None, ge=0)
    custom_metrics: dict[MetricKey, FiniteMetric | None] = Field(default_factory=dict, strict=True)

    @field_validator("accuracy", "precision", "recall", "f1", "loss", mode="before")
    @classmethod
    def require_numeric_metric(cls, value: Any) -> Any:
        if value is not None and (
            isinstance(value, bool) or not isinstance(value, (int, float))
        ):
            raise ValueError("metric must be an integer or float, not a bool or string")
        return value

    @model_validator(mode="after")
    def require_at_least_one_metric(self) -> Self:
        if all(
            value is None
            for value in (self.accuracy, self.precision, self.recall, self.f1, self.loss, *self.custom_metrics.values())
        ):
            raise ValueError("at least one metric must be non-null")
        return self


class ExperimentResultCreate(_ExperimentResultInput):
    pass


class ExperimentResultUpdate(_ExperimentResultInput):
    pass


class ExperimentResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    experiment_id: int
    accuracy: float | None
    precision: float | None
    recall: float | None
    f1: float | None
    loss: float | None
    updated_at: datetime
    custom_metrics: dict[str, float] = Field(default_factory=dict, exclude_if=lambda value: not value)


class ExperimentCompareRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    experiment_ids: list[Annotated[int, Field(strict=True, gt=0)]] = Field(
        strict=True, min_length=2
    )

    @field_validator("experiment_ids")
    @classmethod
    def require_distinct_experiments(cls, value: list[int]) -> list[int]:
        if len(set(value)) != len(value):
            raise ValueError("experiment_ids must not contain duplicates")
        return value


class ComparisonResultMetrics(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    accuracy: float | None
    precision: float | None
    recall: float | None
    f1: float | None
    loss: float | None
    custom_metrics: dict[str, float] = Field(default_factory=dict, exclude_if=lambda value: not value)


class ComparisonExperiment(BaseModel):
    id: int
    experiment_no: str
    model_name: str
    batch_id: int
    project_id: int
    result: ComparisonResultMetrics | None


class BestMetric(BaseModel):
    direction: Literal["max", "min"]
    value: float | None
    experiment_ids: list[int]


class ComparisonBestByMetric(BaseModel):
    accuracy: BestMetric
    precision: BestMetric
    recall: BestMetric
    f1: BestMetric
    loss: BestMetric


class CustomMetricComparison(BaseModel):
    definition: ProjectMetricRead
    project_name: str
    values: dict[int, float | None]
    best: BestMetric


class ExperimentCompareResponse(BaseModel):
    experiments: list[ComparisonExperiment]
    best_by_metric: ComparisonBestByMetric
    custom_metrics: list[CustomMetricComparison] = Field(default_factory=list, exclude_if=lambda value: not value)
