"""Project-scoped metric definitions, shared by all batches and experiments."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Experiment, ExperimentBatch, ExperimentResult, Project, ProjectMetric
from app.schemas import ProjectMetricInput, ProjectMetricRead

router = APIRouter(prefix="/projects/{project_id}/metrics", tags=["Project Metrics"])
DbSession = Annotated[Session, Depends(get_db)]
BUILTINS = [("accuracy", "Accuracy", "max"), ("precision", "Precision", "max"),
            ("recall", "Recall", "max"), ("f1", "F1", "max"), ("loss", "Loss", "min")]


def require_project(project_id: int, db: Session) -> None:
    if db.get(Project, project_id) is None:
        raise HTTPException(404, "Project not found")


def require_metric(project_id: int, metric_id: int, db: Session) -> ProjectMetric:
    require_project(project_id, db)
    metric = db.get(ProjectMetric, metric_id)
    if metric is None or metric.project_id != project_id:
        raise HTTPException(404, "项目指标不存在")
    return metric


def in_use(metric: ProjectMetric, db: Session) -> bool:
    statement = (select(ExperimentResult.id).join(Experiment).join(ExperimentBatch)
                 .where(ExperimentBatch.project_id == metric.project_id,
                        ExperimentResult.custom_metrics[metric.key].as_float().is_not(None)).limit(1))
    return db.scalar(statement) is not None


def commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "该项目已存在相同指标键，或指标写入冲突") from exc


@router.get("", response_model=list[ProjectMetricRead])
def list_metrics(project_id: int, db: DbSession):
    require_project(project_id, db)
    builtin = [ProjectMetricRead(project_id=project_id, key=key, name=name, unit="" if key == "loss" else "比例",
               direction=direction, lower_bound=0, upper_bound=None if key == "loss" else 1, builtin=True)
               for key, name, direction in BUILTINS]
    return [*builtin, *db.scalars(select(ProjectMetric).where(ProjectMetric.project_id == project_id).order_by(ProjectMetric.id))]


@router.post("", response_model=ProjectMetricRead, status_code=201)
def create_metric(project_id: int, payload: ProjectMetricInput, db: DbSession):
    require_project(project_id, db)
    metric = ProjectMetric(project_id=project_id, **payload.model_dump())
    db.add(metric)
    commit(db)
    return metric


@router.put("/{metric_id}", response_model=ProjectMetricRead)
def update_metric(project_id: int, metric_id: int, payload: ProjectMetricInput, db: DbSession):
    metric = require_metric(project_id, metric_id, db)
    if in_use(metric, db) and any(getattr(metric, key) != getattr(payload, key)
                                 for key in ("key", "unit", "direction", "lower_bound", "upper_bound")):
        raise HTTPException(409, "该指标已有实验数值，仅允许修改显示名称；键名、单位、方向和范围不能改变")
    for key, value in payload.model_dump().items():
        setattr(metric, key, value)
    commit(db)
    return metric


@router.delete("/{metric_id}", status_code=204, response_class=Response)
def delete_metric(project_id: int, metric_id: int, db: DbSession):
    metric = require_metric(project_id, metric_id, db)
    if in_use(metric, db):
        raise HTTPException(409, "该指标已有实验数值，不能删除；请先清空相关结果中的该指标")
    db.delete(metric)
    commit(db)
    return Response(status_code=204)
