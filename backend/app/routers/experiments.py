"""Basic Experiment CRUD endpoints with globally unique experiment numbers."""

import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Experiment, ExperimentBatch
from app.schemas import ExperimentCreate, ExperimentRead, ExperimentUpdate


router = APIRouter(tags=["Experiments"])
DbSession = Annotated[Session, Depends(get_db)]
NUMBER_CONFLICT = "Experiment number already exists"


def _get_batch_or_404(batch_id: int, db: Session) -> ExperimentBatch:
    batch = db.get(ExperimentBatch, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="Experiment batch not found")
    return batch


def _get_experiment_or_404(experiment_id: int, db: Session) -> Experiment:
    experiment = db.get(Experiment, experiment_id)
    if experiment is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return experiment


def _check_number_available(
    experiment_no: str, db: Session, exclude_id: int | None = None
) -> None:
    statement = select(Experiment.id).where(Experiment.experiment_no == experiment_no)
    if exclude_id is not None:
        statement = statement.where(Experiment.id != exclude_id)
    if db.scalar(statement.limit(1)) is not None:
        raise HTTPException(status_code=409, detail=NUMBER_CONFLICT)


def _commit_or_conflict(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        # SQLite UNIQUE is the second layer of protection after the active check.
        number_conflict = (
            isinstance(exc.orig, sqlite3.IntegrityError)
            and exc.orig.sqlite_errorcode == sqlite3.SQLITE_CONSTRAINT_UNIQUE
            and "experiments.experiment_no" in str(exc.orig)
        )
        detail = NUMBER_CONFLICT if number_conflict else "Experiment write conflict"
        raise HTTPException(status_code=409, detail=detail) from exc


@router.post("/batches/{batch_id}/experiments", response_model=ExperimentRead, status_code=201)
def create_experiment(
    batch_id: int, payload: ExperimentCreate, db: DbSession
) -> Experiment:
    _get_batch_or_404(batch_id, db)
    _check_number_available(payload.experiment_no, db)
    experiment = Experiment(batch_id=batch_id, **payload.model_dump())
    db.add(experiment)
    _commit_or_conflict(db)
    return experiment


@router.get("/batches/{batch_id}/experiments", response_model=list[ExperimentRead])
def list_batch_experiments(batch_id: int, db: DbSession) -> list[Experiment]:
    _get_batch_or_404(batch_id, db)
    return list(
        db.scalars(
            select(Experiment)
            .where(Experiment.batch_id == batch_id)
            .order_by(Experiment.id.asc())
        )
    )


@router.get("/experiments/{experiment_id}", response_model=ExperimentRead)
def get_experiment(experiment_id: int, db: DbSession) -> Experiment:
    return _get_experiment_or_404(experiment_id, db)


@router.put("/experiments/{experiment_id}", response_model=ExperimentRead)
def update_experiment(
    experiment_id: int, payload: ExperimentUpdate, db: DbSession
) -> Experiment:
    experiment = _get_experiment_or_404(experiment_id, db)
    _check_number_available(payload.experiment_no, db, exclude_id=experiment_id)
    experiment.experiment_no = payload.experiment_no
    experiment.model_name = payload.model_name
    experiment.parameters = payload.parameters
    experiment.notes = payload.notes
    _commit_or_conflict(db)
    return experiment


@router.delete("/experiments/{experiment_id}", status_code=204, response_class=Response)
def delete_experiment(experiment_id: int, db: DbSession) -> Response:
    experiment = _get_experiment_or_404(experiment_id, db)
    db.delete(experiment)
    _commit_or_conflict(db)
    return Response(status_code=204)
