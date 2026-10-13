"""Read current experiment results and compare each metric independently."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Experiment, ExperimentBatch, Project
from app.schemas import (
    BestMetric,
    ComparisonBestByMetric,
    ComparisonExperiment,
    ComparisonResultMetrics,
    ExperimentCompareRequest,
    ExperimentCompareResponse,
    CustomMetricComparison,
    ProjectMetricRead,
)


router = APIRouter(tags=["Experiment Comparison"])
DbSession = Annotated[Session, Depends(get_db)]


def _best_metric(
    experiments: list[ComparisonExperiment],
    metric: str,
    direction: Literal["max", "min"],
) -> BestMetric:
    candidates = []
    for experiment in experiments:
        if experiment.result is not None:
            value = getattr(experiment.result, metric)
            if value is not None:
                candidates.append((experiment.id, value))
    if not candidates:
        return BestMetric(direction=direction, value=None, experiment_ids=[])
    values = [value for _, value in candidates]
    best = max(values) if direction == "max" else min(values)
    return BestMetric(
        direction=direction,
        value=best,
        experiment_ids=[experiment_id for experiment_id, value in candidates if value == best],
    )


@router.post("/experiments/compare", response_model=ExperimentCompareResponse)
def compare_experiments(
    payload: ExperimentCompareRequest, db: DbSession
) -> ExperimentCompareResponse:
    statement = (
        select(Experiment)
        .where(Experiment.id.in_(payload.experiment_ids))
        .options(
            joinedload(Experiment.batch).joinedload(ExperimentBatch.project).joinedload(Project.metrics),
            joinedload(Experiment.result),
        )
    )
    by_id = {experiment.id: experiment for experiment in db.scalars(statement).unique()}
    experiments = []
    for experiment_id in payload.experiment_ids:
        if experiment_id not in by_id:
            raise HTTPException(status_code=404, detail=f"Experiment not found: {experiment_id}")
        experiment = by_id[experiment_id]
        experiments.append(
            ComparisonExperiment(
                id=experiment.id,
                experiment_no=experiment.experiment_no,
                model_name=experiment.model_name,
                batch_id=experiment.batch_id,
                project_id=experiment.batch.project.id,
                result=(
                    ComparisonResultMetrics.model_validate(experiment.result)
                    if experiment.result is not None
                    else None
                ),
            )
        )
    custom_metrics = []
    projects = {by_id[experiment_id].batch.project.id: by_id[experiment_id].batch.project for experiment_id in payload.experiment_ids}
    for project in projects.values():
        for definition in project.metrics:
            values = {item.id: (by_id[item.id].result.custom_metrics.get(definition.key)
                      if item.project_id == project.id and by_id[item.id].result is not None else None)
                      for item in experiments}
            candidates = [(item_id, value) for item_id, value in values.items() if value is not None]
            best = (max if definition.direction == "max" else min)(value for _, value in candidates) if candidates else None
            custom_metrics.append(CustomMetricComparison(
                definition=ProjectMetricRead.model_validate(definition), project_name=project.name, values=values,
                best=BestMetric(direction=definition.direction, value=best,
                                experiment_ids=[item_id for item_id, value in candidates if value == best]),
            ))
    return ExperimentCompareResponse(
        experiments=experiments,
        custom_metrics=custom_metrics,
        best_by_metric=ComparisonBestByMetric(
            accuracy=_best_metric(experiments, "accuracy", "max"),
            precision=_best_metric(experiments, "precision", "max"),
            recall=_best_metric(experiments, "recall", "max"),
            f1=_best_metric(experiments, "f1", "max"),
            loss=_best_metric(experiments, "loss", "min"),
        ),
    )
