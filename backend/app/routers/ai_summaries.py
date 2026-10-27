"""Optional manual AI summaries; no writes, history table or startup requests."""

from collections import OrderedDict
from threading import Lock
from time import monotonic
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.ai_provider import build_messages, call_deepseek
from app.ai_schemas import GenerateSummary, SnapshotCheck, SummarySelection
from app.ai_settings import AISettings, get_ai_settings
from app.ai_snapshot import build_snapshot, utc_now
from app.database import get_db

router = APIRouter(prefix="/ai/summaries", tags=["AI Summaries"])
DbSession = Annotated[Session, Depends(get_db)]
Settings = Annotated[AISettings, Depends(get_ai_settings)]
_gate = Lock()
_recent: OrderedDict[str, float] = OrderedDict()


@router.get("/status")
def status(settings: Settings):
    reason = ""
    try:
        settings.require_ready()
    except HTTPException as exc:
        reason = exc.detail
    return {"ready": not reason, "message": reason or "已配置，只有确认发送时才调用 DeepSeek。",
            "max_experiments": settings.max_experiments}


@router.post("/preview")
def preview(payload: SummarySelection, db: DbSession, settings: Settings):
    snapshot = build_snapshot(db, payload, settings)
    messages = build_messages(snapshot, settings)
    return {**snapshot, "messages": messages, "configured_model": settings.model}


@router.post("/check")
def check(payload: SnapshotCheck, db: DbSession, settings: Settings):
    snapshot = build_snapshot(db, payload, settings)
    return {"current": snapshot["fingerprint"] == payload.fingerprint}


@router.post("/generate")
async def generate(payload: GenerateSummary, db: DbSession, settings: Settings):
    settings.require_ready()
    if not _gate.acquire(blocking=False):
        raise HTTPException(409, "已有 AI 总结正在生成，请等待完成。")
    try:
        now = monotonic()
        while _recent and next(iter(_recent.values())) < now - 300:
            _recent.popitem(last=False)
        key = str(payload.request_id)
        if key in _recent:
            raise HTTPException(409, "该生成请求已发送；为避免重复计费，请重新预览后手动生成。")
        if len(_recent) >= 256:
            raise HTTPException(429, "短时间生成次数过多，请稍后重试。")
        snapshot = await run_in_threadpool(build_snapshot, db, payload, settings)
        if snapshot["fingerprint"] != payload.fingerprint:
            raise HTTPException(409, "预览后实验数据或配置已变化，请重新预览并确认发送。")
        build_messages(snapshot, settings)
        _recent[key] = monotonic()  # Reserve before any provider I/O, including failures.
        answer = await call_deepseek(snapshot, settings)
        stale = False
        try:
            latest = await run_in_threadpool(build_snapshot, db, payload, settings)
            stale = latest["fingerprint"] != snapshot["fingerprint"]
        except HTTPException:
            stale = True
        return {**answer, "fingerprint": snapshot["fingerprint"], "fetched_at": snapshot["fetched_at"],
                "generated_at": utc_now(), "stale": stale, "facts": snapshot["facts"], "data": snapshot["data"]}
    finally:
        _gate.release()
