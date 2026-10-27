"""Read-only snapshots and deterministic evidence for AI explanations."""

from datetime import UTC, datetime
import hashlib
import json
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.ai_schemas import SummarySelection
from app.ai_settings import AISettings
from app.models import Experiment
from app.routers.compare import compare_experiments
from app.schemas import ExperimentCompareRequest

RULE_VERSION = "ai-summary-v3"
BUILTINS = ("accuracy", "precision", "recall", "f1", "loss")
WARNINGS = [
    "同一项目不代表数据集、测试划分、硬件和指标口径一致；未提供的评测条件不能视为一致。",
    "单次实验不能证明统计显著或稳定提升；多个参数同时变化时不能判定单一参数的因果作用。",
    "AI 叙述需人工核对；最佳和差值以本页确定性事实为准。",
]


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def leaf_values(value: Any, pointer: str = "", depth: int = 0) -> dict[str, Any]:
    # JSON Pointer escapes distinguish literal dots, slashes, tildes and array indices.
    if depth > 20:
        raise HTTPException(422, "参数嵌套过深，AI 总结最多支持 20 层。")
    children = value.items() if isinstance(value, dict) else enumerate(value) if isinstance(value, list) else None
    if children is None:
        return {pointer: value}
    leaves: dict[str, Any] = {}
    for key, child in children:
        escaped = str(key).replace("~", "~0").replace("/", "~1")
        leaves.update(leaf_values(child, f"{pointer}/{escaped}", depth + 1))
        if len(leaves) > 512:
            raise HTTPException(422, "参数叶子字段过多，AI 总结最多支持每个实验 512 项。")
    return leaves


def build_snapshot(db: Session, selection: SummarySelection, settings: AISettings) -> dict:
    if settings.error:
        raise HTTPException(503, settings.error)
    if len(selection.experiment_ids) > settings.max_experiments:
        raise HTTPException(422, f"本地配置最多允许 {settings.max_experiments} 个实验。")
    try:
        # sqlite3 legacy transaction mode does not BEGIN for SELECT by itself.
        db.connection().exec_driver_sql("BEGIN")
        return _build(db, selection, settings)
    except (ValueError, TypeError, OverflowError):
        raise HTTPException(422, "实验数据包含无法用于 AI 总结的非有限数值或非法 JSON。") from None
    finally:
        # No transaction or checked-out connection stays open during the paid request.
        db.rollback()


def _build(db: Session, selection: SummarySelection, settings: AISettings) -> dict:
    comparison = compare_experiments(ExperimentCompareRequest(
        experiment_ids=selection.experiment_ids, baseline_experiment_id=selection.baseline_experiment_id,
    ), db).model_dump(mode="json")
    if len({item["project_id"] for item in comparison["experiments"]}) != 1:
        raise HTTPException(422, "AI 总结第一版仅支持同一项目；跨项目仍可使用原比较功能。")
    rows = {item.id: item for item in db.scalars(select(Experiment).where(
        Experiment.id.in_(selection.experiment_ids)
    ).options(joinedload(Experiment.batch))).unique()}
    parameters = {item_id: leaf_values(rows[item_id].parameters) for item_id in selection.experiment_ids}
    paths = sorted(set().union(*(item.keys() for item in parameters.values())))
    if len(paths) > 512 or any(len(path) > 1024 for path in paths):
        raise HTTPException(422, "可选参数路径过多或过长，请缩小实验选择。")
    if not set(selection.parameter_paths) <= set(paths):
        raise HTTPException(422, "所选参数路径已不存在，请重新选择并预览。")
    project_id = comparison["experiments"][0]["project_id"]
    facts = []
    deltas = {(item["project_id"], item["key"]): item for item in (comparison.get("baseline_comparison") or {}).get("metrics", [])}
    for key in BUILTINS:
        best = comparison["best_by_metric"][key]
        facts.append({
            "id": f"system:{key}", "key": key, "name": key, "project_id": None,
            "unit": "" if key == "loss" else "比例", "direction": best["direction"],
            "lower_bound": 0, "upper_bound": None if key == "loss" else 1,
            "values": {str(item["id"]): item["result"][key] if item["result"] else None for item in comparison["experiments"]},
            "best": best, "baseline": deltas.get((None, key)),
        })
    for item in comparison.get("custom_metrics", []):
        definition = item["definition"]
        facts.append({
            **{key: definition[key] for key in ("key", "name", "project_id", "unit", "direction", "lower_bound", "upper_bound")},
            "id": f"custom:{project_id}:{definition['id']}:{definition['key']}",
            "values": {str(key): value for key, value in item["values"].items()}, "best": item["best"],
            "baseline": deltas.get((project_id, definition["key"])),
        })
    comparable = [fact["id"] for fact in facts if sum(value is not None for value in fact["values"].values()) >= 2]
    if not comparable:
        raise HTTPException(422, "至少两个实验须有结果，且至少一项指标在两个实验中都有值。")
    metric_ids = {fact["id"] for fact in facts}
    if selection.primary_metric is not None and selection.primary_metric not in comparable:
        raise HTTPException(422, "主指标不存在或不足两个有效实验，请重新选择。")
    experiment_data = []
    for item in comparison["experiments"]:
        experiment_data.append({
            **{key: item[key] for key in ("id", "experiment_no", "model_name", "project_id", "batch_id")},
            "has_result": item["result"] is not None,
            "parameters": {path: {"present": path in parameters[item["id"]], "value": parameters[item["id"]].get(path)}
                           for path in sorted(selection.parameter_paths)},
        })
    evidence = [{"id": f"experiment:{item['id']}", "experiment_ids": [item["id"]], "metric_ids": [], "data": item}
                for item in experiment_data]
    evidence.extend({"id": f"metric:{fact['id']}", "experiment_ids": selection.experiment_ids,
                     "metric_ids": [fact["id"]], "data": fact} for fact in facts)
    data = {
        "rule_version": RULE_VERSION, "project_id": project_id, "experiment_ids": selection.experiment_ids,
        "baseline_experiment_id": selection.baseline_experiment_id, "primary_metric": selection.primary_metric,
        "warnings": WARNINGS, "evidence": evidence,
    }
    # Internal config detects edits even to parameters the user chose not to send.
    fingerprint = hashlib.sha256(canonical({
        "data": data, "parameters": {key: rows[key].parameters for key in selection.experiment_ids},
        "model": settings.model,
    }).encode("utf-8")).hexdigest()
    return {
        "fingerprint": fingerprint, "fetched_at": utc_now(), "data": data, "facts": facts,
        "parameter_paths": paths, "metric_options": [{"id": fact["id"], "name": fact["name"], "unit": fact["unit"],
                                                       "comparable": fact["id"] in comparable} for fact in facts],
        "metric_ids": sorted(metric_ids),
    }
