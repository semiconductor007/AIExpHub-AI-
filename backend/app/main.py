"""FastAPI application with experiment management, comparison and health endpoints."""

from contextlib import asynccontextmanager
from math import isfinite

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.database import SessionLocal, engine, init_db
from app.routers import batches, compare, experiments, projects, results


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
app.include_router(compare.router)
app.include_router(experiments.router)
app.include_router(results.router)


@app.exception_handler(RequestValidationError)
async def validation_error_response(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    # Invalid NaN/Infinity may appear in error inputs, which must still be valid JSON.
    detail = jsonable_encoder(
        exc.errors(),
        custom_encoder={float: lambda value: value if isfinite(value) else str(value)},
    )
    return JSONResponse(status_code=422, content={"detail": detail})


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
