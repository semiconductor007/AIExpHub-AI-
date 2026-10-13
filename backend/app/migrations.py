"""Upgrade the legacy SQLite result table transactionally, with a backup first."""

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import Engine
from sqlalchemy.schema import CreateTable


def upgrade_project_metrics(engine: Engine) -> Path | None:
    from app.models import ExperimentResult

    with engine.connect() as connection:
        columns = connection.exec_driver_sql("PRAGMA table_info(experiment_results)").all()
    if not columns or any(row[1] == "custom_metrics" for row in columns):
        return None

    database = engine.url.database
    if not database or database == ":memory:":
        raise RuntimeError("Legacy migration requires a file-backed SQLite database")
    path = Path(database)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    backup = path.with_name(f"{path.stem}.pre-project-metrics-{stamp}.db")
    raw = engine.raw_connection()
    connection = raw.driver_connection
    previous_autocommit = connection.autocommit
    try:
        connection.rollback()
        connection.autocommit = True
        with sqlite3.connect(backup) as destination:
            connection.backup(destination)
        connection.execute("PRAGMA foreign_keys=OFF")
        connection.execute("BEGIN IMMEDIATE")
        try:
            # A second starter may have upgraded the schema since the first check.
            if any(row[1] == "custom_metrics" for row in connection.execute("PRAGMA table_info(experiment_results)")):
                connection.execute("ROLLBACK")
                return None
            ddl = str(CreateTable(ExperimentResult.__table__).compile(engine))
            connection.execute(ddl.replace("CREATE TABLE experiment_results", "CREATE TABLE experiment_results_upgrade", 1))
            fields = "id, experiment_id, accuracy, precision, recall, f1, loss, updated_at"
            connection.execute(
                f"INSERT INTO experiment_results_upgrade ({fields}, custom_metrics) "
                f"SELECT {fields}, '{{}}' FROM experiment_results"
            )
            connection.execute("DROP TABLE experiment_results")
            connection.execute("ALTER TABLE experiment_results_upgrade RENAME TO experiment_results")
            if connection.execute("PRAGMA foreign_key_check").fetchall():
                raise RuntimeError("Foreign key check failed during migration")
            connection.execute("PRAGMA user_version=1")
            connection.execute("COMMIT")
        except Exception:
            connection.execute("ROLLBACK")
            raise
    finally:
        connection.execute("PRAGMA foreign_keys=ON")
        connection.autocommit = previous_autocommit
        raw.close()
    return backup
