"""FastAPI application with project, batch and health endpoints."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.database import SessionLocal, engine, init_db
from app.routers import batches, projects


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        init_db()
        yield
    finally:
        engine.dispose()


app = FastAPI(title="AIExpHub API", lifespan=lifespan)
app.include_router(projects.router)
app.include_router(batches.router)


@app.get("/health", tags=["Health"])
def health() -> dict[str, str]:
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1")).scalar_one()
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Database connection unavailable",
        ) from exc

    return {"status": "ok", "service": "AIExpHub API"}
