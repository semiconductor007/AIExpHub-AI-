"""Basic Project CRUD endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ExperimentBatch, Project
from app.schemas import ProjectCreate, ProjectRead, ProjectUpdate


router = APIRouter(prefix="/projects", tags=["Projects"])
DbSession = Annotated[Session, Depends(get_db)]


def _get_project_or_404(project_id: int, db: Session) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _commit_or_conflict(db: Session, detail: str) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=detail) from exc


@router.post("", response_model=ProjectRead, status_code=201)
def create_project(payload: ProjectCreate, db: DbSession) -> Project:
    project = Project(**payload.model_dump())
    db.add(project)
    _commit_or_conflict(db, "Project write conflict")
    return project


@router.get("", response_model=list[ProjectRead])
def list_projects(db: DbSession) -> list[Project]:
    return list(db.scalars(select(Project).order_by(Project.id.asc())))


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(project_id: int, db: DbSession) -> Project:
    return _get_project_or_404(project_id, db)


@router.put("/{project_id}", response_model=ProjectRead)
def update_project(project_id: int, payload: ProjectUpdate, db: DbSession) -> Project:
    project = _get_project_or_404(project_id, db)
    project.name = payload.name
    project.description = payload.description
    _commit_or_conflict(db, "Project write conflict")
    return project


@router.delete("/{project_id}", status_code=204, response_class=Response)
def delete_project(project_id: int, db: DbSession) -> Response:
    project = _get_project_or_404(project_id, db)
    has_batch = db.scalar(
        select(ExperimentBatch.id).where(ExperimentBatch.project_id == project_id).limit(1)
    )
    if has_batch is not None:
        raise HTTPException(status_code=409, detail="Project has existing batches")
    db.delete(project)
    _commit_or_conflict(db, "Project has existing batches")
    return Response(status_code=204)
