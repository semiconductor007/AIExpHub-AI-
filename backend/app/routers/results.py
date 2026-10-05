"""Create, read and fully replace the current result of an experiment."""

import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Experiment, ExperimentResult
from app.schemas import (
    ExperimentResultCreate,
    ExperimentResultRead,
    ExperimentResultUpdate,
)


router = APIRouter(tags=["Experiment Results"])
DbSession = Annotated[Session, Depends(get_db)]
RESULT_CONFLICT = "Experiment result already exists"


def _get_experiment_or_404(experiment_id: int, db: Session) -> Experiment:
    experiment = db.get(Experiment, experiment_id)
    if experiment is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return experiment


def _find_result(experiment_id: int, db: Session) -> ExperimentResult | None:
    return db.scalar(
        select(ExperimentResult).where(ExperimentResult.experiment_id == experiment_id)
    )


def _get_result_or_404(experiment_id: int, db: Session) -> ExperimentResult:
    result = _find_result(experiment_id, db)
    if result is None:
        raise HTTPException(status_code=404, detail="Experiment result not found")
    return result


def _commit_or_conflict(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        duplicate_result = (
            isinstance(exc.orig, sqlite3.IntegrityError)
            and exc.orig.sqlite_errorcode == sqlite3.SQLITE_CONSTRAINT_UNIQUE
            and "experiment_results.experiment_id" in str(exc.orig)
        )
        detail = RESULT_CONFLICT if duplicate_result else "Experiment result write conflict"
        raise HTTPException(status_code=409, detail=detail) from exc


@router.post(
    "/experiments/{experiment_id}/result",
    response_model=ExperimentResultRead,
    status_code=201,
)
def create_result(
    experiment_id: int, payload: ExperimentResultCreate, db: DbSession
) -> ExperimentResult:
    _get_experiment_or_404(experiment_id, db)
    if _find_result(experiment_id, db) is not None:
        raise HTTPException(status_code=409, detail=RESULT_CONFLICT)
    result = ExperimentResult(experiment_id=experiment_id, **payload.model_dump())
    db.add(result)
    _commit_or_conflict(db)
    return result


@router.get("/experiments/{experiment_id}/result", response_model=ExperimentResultRead)
def get_result(experiment_id: int, db: DbSession) -> ExperimentResult:
    _get_experiment_or_404(experiment_id, db)
    return _get_result_or_404(experiment_id, db)


@router.put("/experiments/{experiment_id}/result", response_model=ExperimentResultRead)
def update_result(
    experiment_id: int, payload: ExperimentResultUpdate, db: DbSession
) -> ExperimentResult:
    _get_experiment_or_404(experiment_id, db)
    result = _get_result_or_404(experiment_id, db)
    # Include default None values: PUT clears every omitted metric.
    for field, value in payload.model_dump().items():
        setattr(result, field, value)
    _commit_or_conflict(db)
    return result
