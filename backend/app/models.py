"""Core database models; application-level input validation comes later."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utc_now() -> datetime:
    """Store UTC timestamps without an offset in SQLite DateTime columns."""
    return datetime.now(UTC).replace(tzinfo=None)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now, server_default=func.current_timestamp()
    )

    # Let SQLite enforce RESTRICT, including when the collection is loaded.
    batches: Mapped[list[ExperimentBatch]] = relationship(
        back_populates="project", passive_deletes="all"
    )


class ExperimentBatch(Base):
    __tablename__ = "experiment_batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now, server_default=func.current_timestamp()
    )

    project: Mapped[Project] = relationship(back_populates="batches")
    experiments: Mapped[list[Experiment]] = relationship(
        back_populates="batch", passive_deletes="all"
    )


class Experiment(Base):
    __tablename__ = "experiments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[int] = mapped_column(
        ForeignKey("experiment_batches.id", ondelete="RESTRICT"), nullable=False
    )
    experiment_no: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    model_name: Mapped[str] = mapped_column(String, nullable=False)
    parameters: Mapped[dict[str, Any]] = mapped_column(
        JSON(none_as_null=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now, server_default=func.current_timestamp()
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    batch: Mapped[ExperimentBatch] = relationship(back_populates="experiments")
    # SQLite owns result deletion; do not NULL the FK even for loaded results.
    result: Mapped[ExperimentResult | None] = relationship(
        back_populates="experiment", uselist=False, passive_deletes="all"
    )


class ExperimentResult(Base):
    __tablename__ = "experiment_results"
    __table_args__ = (
        CheckConstraint(
            "accuracy IS NULL OR (accuracy >= 0 AND accuracy <= 1)",
            name="ck_experiment_results_accuracy_range",
        ),
        CheckConstraint(
            "precision IS NULL OR (precision >= 0 AND precision <= 1)",
            name="ck_experiment_results_precision_range",
        ),
        CheckConstraint(
            "recall IS NULL OR (recall >= 0 AND recall <= 1)",
            name="ck_experiment_results_recall_range",
        ),
        CheckConstraint(
            "f1 IS NULL OR (f1 >= 0 AND f1 <= 1)",
            name="ck_experiment_results_f1_range",
        ),
        CheckConstraint(
            "loss IS NULL OR loss >= 0",
            name="ck_experiment_results_loss_range",
        ),
        CheckConstraint(
            "accuracy IS NOT NULL OR precision IS NOT NULL OR recall IS NOT NULL "
            "OR f1 IS NOT NULL OR loss IS NOT NULL",
            name="ck_experiment_results_at_least_one_metric",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    experiment_id: Mapped[int] = mapped_column(
        ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    precision: Mapped[float | None] = mapped_column(Float, nullable=True)
    recall: Mapped[float | None] = mapped_column(Float, nullable=True)
    f1: Mapped[float | None] = mapped_column(Float, nullable=True)
    loss: Mapped[float | None] = mapped_column(Float, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=utc_now,
        server_default=func.current_timestamp(),
        onupdate=utc_now,
    )

    experiment: Mapped[Experiment] = relationship(back_populates="result")
