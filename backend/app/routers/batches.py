"""Basic ExperimentBatch CRUD endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Experiment, ExperimentBatch, Project
from app.schemas import BatchCreate, BatchRead, BatchUpdate


router = APIRouter(tags=["Experiment Batches"])
DbSession = Annotated[Session, Depends(get_db)]


def _get_project_or_404(project_id: int, db: Session) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _get_batch_or_404(batch_id: int, db: Session) -> ExperimentBatch:
    batch = db.get(ExperimentBatch, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="Experiment batch not found")
    return batch


def _commit_or_conflict(db: Session, detail: str) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=detail) from exc


@router.post("/projects/{project_id}/batches", response_model=BatchRead, status_code=201)
def create_batch(project_id: int, payload: BatchCreate, db: DbSession) -> ExperimentBatch:
    _get_project_or_404(project_id, db)
    batch = ExperimentBatch(project_id=project_id, **payload.model_dump())
    db.add(batch)
    _commit_or_conflict(db, "Experiment batch write conflict")
    return batch


@router.get("/projects/{project_id}/batches", response_model=list[BatchRead])
def list_project_batches(project_id: int, db: DbSession) -> list[ExperimentBatch]:
    _get_project_or_404(project_id, db)
    return list(
        db.scalars(
            select(ExperimentBatch)
            .where(ExperimentBatch.project_id == project_id)
            .order_by(ExperimentBatch.id.asc())
        )
    )


@router.get("/batches/{batch_id}", response_model=BatchRead)
def get_batch(batch_id: int, db: DbSession) -> ExperimentBatch:
    return _get_batch_or_404(batch_id, db)


@router.put("/batches/{batch_id}", response_model=BatchRead)
def update_batch(batch_id: int, payload: BatchUpdate, db: DbSession) -> ExperimentBatch:
    batch = _get_batch_or_404(batch_id, db)
    batch.name = payload.name
    batch.description = payload.description
    _commit_or_conflict(db, "Experiment batch write conflict")
    return batch


@router.delete("/batches/{batch_id}", status_code=204, response_class=Response)
def delete_batch(batch_id: int, db: DbSession) -> Response:
    batch = _get_batch_or_404(batch_id, db)
    has_experiment = db.scalar(
        select(Experiment.id).where(Experiment.batch_id == batch_id).limit(1)
    )
    if has_experiment is not None:
        raise HTTPException(
            status_code=409, detail="Experiment batch has existing experiments"
        )
    db.delete(batch)
    _commit_or_conflict(db, "Experiment batch has existing experiments")
    return Response(status_code=204)
