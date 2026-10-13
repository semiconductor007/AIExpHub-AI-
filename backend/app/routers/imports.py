"""Preview and atomically import new experiments into one selected batch."""

from collections import Counter
from math import isfinite
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Experiment, ExperimentBatch, ExperimentResult
from app.routers.metrics import list_metrics, require_project
from app.routers.results import _result_payload
from app.schemas import ExperimentCreate, ExperimentRead, ExperimentResultCreate, FiniteMetric

router = APIRouter(tags=["Experiment Import"])
DbSession = Annotated[Session, Depends(get_db)]


class MetricReference(BaseModel):
    """Exported definitions document units and detect changed evaluation criteria."""

    model_config = ConfigDict(extra="forbid")
    key: str
    name: str
    unit: str
    direction: Literal["max", "min"]
    lower_bound: FiniteMetric | None = None
    upper_bound: FiniteMetric | None = None


class ImportDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    format_version: Literal[1] = 1
    project_id: Annotated[int, Field(strict=True, gt=0)] | None = None
    metric_definitions: list[MetricReference] | None = None
    experiments: list[Any] = Field(strict=True, min_length=1, max_length=100)


class ImportRow(ExperimentCreate):
    result: dict[str, Any] | None = Field(default=None, strict=True)

    @field_validator("parameters")
    @classmethod
    def finite_parameters(cls, value: dict) -> dict:
        def check(item):
            if isinstance(item, float) and not isfinite(item):
                raise ValueError("JSON 参数不能包含 NaN 或 Infinity")
            if isinstance(item, dict):
                for child in item.values(): check(child)
            elif isinstance(item, list):
                for child in item: check(child)
        check(value)
        return value


class PreviewRow(BaseModel):
    row: int
    experiment_no: str | None
    normalized: dict[str, Any] | None
    errors: list[str]


class ImportPreview(BaseModel):
    can_import: bool
    total: int
    valid_count: int
    rows: list[PreviewRow]


def definitions(project_id: int, db: Session) -> list[dict]:
    return [{key: getattr(item, key) for key in ("key", "name", "unit", "direction", "lower_bound", "upper_bound")}
            for item in list_metrics(project_id, db)]


@router.get("/projects/{project_id}/import-template", response_model=ImportDocument)
def import_template(project_id: int, db: DbSession):
    require_project(project_id, db)
    metric_definitions = definitions(project_id, db)
    return ImportDocument(project_id=project_id, metric_definitions=metric_definitions, experiments=[{
        "experiment_no": "REPLACE-WITH-UNIQUE-NUMBER", "model_name": "请填写模型名称",
        "parameters": {"seed": 42}, "notes": "示例：请替换为真实配置与结果；result 为 null 可先导入无结果实验",
        "result": {item["key"]: None for item in metric_definitions},
    }])


def schema_errors(exc: ValidationError) -> list[str]:
    messages = {"missing": "必填字段缺失", "extra_forbidden": "不支持该字段", "string_too_short": "不能为空或只有空白",
                "dict_type": "必须是 JSON 对象", "string_type": "必须是文本", "float_type": "必须是数值或 null",
                "finite_number": "必须是有限数值", "greater_than_equal": "小于允许的下限", "less_than_equal": "大于允许的上限"}
    return [f"{'.'.join(map(str, error['loc'])) or '记录'}：{messages.get(error['type'], error['msg'])}"
            for error in exc.errors(include_input=False, include_context=False)]


def preview_document(batch_id: int, document: ImportDocument, db: Session) -> ImportPreview:
    batch = db.get(ExperimentBatch, batch_id)
    if batch is None:
        raise HTTPException(404, "Experiment batch not found")
    if document.project_id is not None and document.project_id != batch.project_id:
        raise HTTPException(422, "文件所属项目与当前批次不一致，请选择文件对应的项目")
    current = {item["key"]: item for item in definitions(batch.project_id, db)}
    if document.metric_definitions is not None:
        for reference in document.metric_definitions:
            item = current.get(reference.key)
            if item is None or any(item[key] != getattr(reference, key) for key in ("unit", "direction", "lower_bound", "upper_bound")):
                raise HTTPException(422, f"指标 {reference.key} 的定义已变化或不存在，请重新下载模板并核对单位、方向和范围")
    rows = []
    for index, value in enumerate(document.experiments, 1):
        number = value.get("experiment_no") if isinstance(value, dict) else None
        number = number.strip().upper() if isinstance(number, str) else None
        normalized = None
        errors = []
        try:
            row = ImportRow.model_validate(value)
            normalized = row.model_dump()
            if row.result is not None:
                unknown = row.result.keys() - current.keys()
                if unknown:
                    raise HTTPException(422, f"项目未定义指标：{'、'.join(sorted(unknown))}")
                payload = ExperimentResultCreate.model_validate({
                    **{key: row.result[key] for key in ("accuracy", "precision", "recall", "f1", "loss") if key in row.result},
                    "custom_metrics": {key: val for key, val in row.result.items() if key not in {"accuracy", "precision", "recall", "f1", "loss"}},
                })
                result = _result_payload(Experiment(batch_id=batch_id), payload, db)
                normalized["result"] = {**{key: result[key] for key in ("accuracy", "precision", "recall", "f1", "loss")}, **result["custom_metrics"]}
        except ValidationError as exc:
            errors = schema_errors(exc)
        except HTTPException as exc:
            errors = [str(exc.detail)]
        rows.append(PreviewRow(row=index, experiment_no=number, normalized=normalized if not errors else None, errors=errors))
    counts = Counter(row.experiment_no for row in rows if row.experiment_no)
    existing = set(db.scalars(select(Experiment.experiment_no).where(Experiment.experiment_no.in_(counts))))
    for row in rows:
        if row.experiment_no and counts[row.experiment_no] > 1:
            row.errors.append("文件内实验编号重复（trim + uppercase 后视为同一编号）")
        if row.experiment_no in existing:
            row.errors.append("实验编号已存在于系统，不会覆盖已有实验")
    valid = sum(not row.errors for row in rows)
    return ImportPreview(can_import=valid == len(rows), total=len(rows), valid_count=valid, rows=rows)


@router.post("/batches/{batch_id}/imports/preview", response_model=ImportPreview)
def preview_import(batch_id: int, payload: ImportDocument, db: DbSession):
    return preview_document(batch_id, payload, db)


@router.post("/batches/{batch_id}/imports", response_model=list[ExperimentRead], status_code=201)
def confirm_import(batch_id: int, payload: ImportDocument, db: DbSession):
    preview = preview_document(batch_id, payload, db)
    if not preview.can_import:
        raise HTTPException(422, preview.model_dump())
    created = []
    try:
        for item in preview.rows:
            row = ImportRow.model_validate(item.normalized)
            experiment = Experiment(batch_id=batch_id, **row.model_dump(exclude={"result"}))
            db.add(experiment)
            db.flush()
            if row.result is not None:
                values = row.result
                result = ExperimentResultCreate.model_validate({
                    **{key: values[key] for key in ("accuracy", "precision", "recall", "f1", "loss") if key in values},
                    "custom_metrics": {key: val for key, val in values.items() if key not in {"accuracy", "precision", "recall", "f1", "loss"}},
                })
                db.add(ExperimentResult(experiment_id=experiment.id, **_result_payload(experiment, result, db)))
            created.append(experiment)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "导入冲突，整批未保存；编号可能已被使用或项目指标已变化，请重新预览") from exc
    return created
