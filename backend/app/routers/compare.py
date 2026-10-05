"""Read current experiment results and compare each metric independently."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Experiment, ExperimentBatch
from app.schemas import (
    BestMetric,
    ComparisonBestByMetric,
    ComparisonExperiment,
    ComparisonResultMetrics,
    ExperimentCompareRequest,
    ExperimentCompareResponse,
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
            joinedload(Experiment.batch).joinedload(ExperimentBatch.project),
            joinedload(Experiment.result),
        )
    )
    by_id = {experiment.id: experiment for experiment in db.scalars(statement)}
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
    return ExperimentCompareResponse(
        experiments=experiments,
        best_by_metric=ComparisonBestByMetric(
            accuracy=_best_metric(experiments, "accuracy", "max"),
            precision=_best_metric(experiments, "precision", "max"),
            recall=_best_metric(experiments, "recall", "max"),
            f1=_best_metric(experiments, "f1", "max"),
            loss=_best_metric(experiments, "loss", "min"),
        ),
    )
