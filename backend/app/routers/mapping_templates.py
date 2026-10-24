"""Project-local reusable result mappings with explicit custom metric identities."""

from fastapi import APIRouter, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.mapping_schemas import TemplateInput, TemplateRead, TemplateRename
from app.models import ProjectMetric, ResultMappingEntry, ResultMappingTemplate
from app.routers.metrics import BUILTINS, DbSession, require_project

router = APIRouter(prefix="/projects/{project_id}/result-mapping-templates", tags=["Result Mapping Templates"])
BUILTIN_KEYS = {item[0] for item in BUILTINS}


def require_template(project_id: int, template_id: int, db) -> ResultMappingTemplate:
    require_project(project_id, db)
    template = db.get(ResultMappingTemplate, template_id)
    if template is None or template.project_id != project_id:
        raise HTTPException(404, "映射模板不存在")
    return template


def entries(project_id: int, payload: TemplateInput, db) -> list[ResultMappingEntry]:
    definitions = {metric.id: metric for metric in db.scalars(select(ProjectMetric).where(ProjectMetric.project_id == project_id))}
    for item in payload.mappings:
        if item.builtin:
            if item.metric_id is not None or item.metric_key not in BUILTIN_KEYS:
                raise HTTPException(422, "系统指标映射身份无效")
        else:
            metric = definitions.get(item.metric_id)
            if metric is None or metric.key != item.metric_key:
                raise HTTPException(422, "自定义指标不存在、已变化或不属于当前项目，请刷新并重新映射")
    return [ResultMappingEntry(**item.model_dump()) for item in payload.mappings]


def commit(db) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "当前项目已存在同名映射模板，或关联指标已变化") from exc


@router.get("", response_model=list[TemplateRead])
def list_templates(project_id: int, db: DbSession):
    require_project(project_id, db)
    return list(db.scalars(select(ResultMappingTemplate).where(ResultMappingTemplate.project_id == project_id).order_by(ResultMappingTemplate.id)))


@router.post("", response_model=TemplateRead, status_code=201)
def create_template(project_id: int, payload: TemplateInput, db: DbSession):
    require_project(project_id, db)
    template = ResultMappingTemplate(project_id=project_id, name=payload.name, mappings=entries(project_id, payload, db))
    db.add(template)
    commit(db)
    return template


@router.put("/{template_id}", response_model=TemplateRead)
def update_template(project_id: int, template_id: int, payload: TemplateInput, db: DbSession):
    template = require_template(project_id, template_id, db)
    replacement = entries(project_id, payload, db)
    template.mappings.clear()
    db.flush()  # Delete previous keys before inserting the same keys in a replacement.
    template.name = payload.name
    template.mappings.extend(replacement)
    commit(db)
    return template


@router.patch("/{template_id}", response_model=TemplateRead)
def rename_template(project_id: int, template_id: int, payload: TemplateRename, db: DbSession):
    template = require_template(project_id, template_id, db)
    template.name = payload.name
    commit(db)
    return template


@router.delete("/{template_id}", status_code=204, response_class=Response)
def delete_template(project_id: int, template_id: int, db: DbSession):
    template = require_template(project_id, template_id, db)
    db.delete(template)
    commit(db)
    return Response(status_code=204)
