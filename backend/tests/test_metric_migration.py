"""Upgrade real legacy layouts in temporary files without losing existing rows."""

import sqlite3
from types import SimpleNamespace

import pytest
from sqlalchemy import URL, create_engine, event
from sqlalchemy.engine import Connection

from app.database import Base, enable_sqlite_foreign_keys
from app.metric_constraints import install_metric_constraints
from app.migrations import upgrade_project_metrics


def legacy_database(path, bad_foreign_key=False):
    with sqlite3.connect(path) as db:
        db.executescript("""
            CREATE TABLE projects (id INTEGER PRIMARY KEY, name TEXT NOT NULL, description TEXT, created_at DATETIME NOT NULL);
            CREATE TABLE experiment_batches (id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE RESTRICT, name TEXT NOT NULL, description TEXT, created_at DATETIME NOT NULL);
            CREATE TABLE experiments (id INTEGER PRIMARY KEY, batch_id INTEGER NOT NULL REFERENCES experiment_batches(id) ON DELETE RESTRICT, experiment_no TEXT UNIQUE NOT NULL, model_name TEXT NOT NULL, parameters JSON NOT NULL, created_at DATETIME NOT NULL, notes TEXT);
            CREATE TABLE experiment_results (id INTEGER PRIMARY KEY, experiment_id INTEGER NOT NULL UNIQUE REFERENCES experiments(id) ON DELETE CASCADE,
                accuracy FLOAT CHECK (accuracy IS NULL OR (accuracy>=0 AND accuracy<=1)), precision FLOAT, recall FLOAT, f1 FLOAT, loss FLOAT CHECK(loss IS NULL OR loss>=0), updated_at DATETIME NOT NULL,
                CHECK (accuracy IS NOT NULL OR precision IS NOT NULL OR recall IS NOT NULL OR f1 IS NOT NULL OR loss IS NOT NULL));
            INSERT INTO projects VALUES (8, 'Legacy', NULL, '2026-01-01 00:00:00');
            INSERT INTO experiment_batches VALUES (9, 8, 'Legacy batch', NULL, '2026-01-01 00:00:00');
            INSERT INTO experiments VALUES (12, 9, 'LEGACY-001', 'Model', '{"seed":42}', '2026-01-01 00:00:00', 'keep');
        """)
        db.execute("INSERT INTO experiment_results VALUES(21, ?, 0.85, NULL, NULL, NULL, 0, '2026-01-01 01:00:00')", (999 if bad_foreign_key else 12,))
        return {table: db.execute(f"SELECT * FROM {table} ORDER BY id").fetchall() for table in ["projects", "experiment_batches", "experiments", "experiment_results"]}


def test_migration_preserves_and_is_idempotent(tmp_path):
    path = tmp_path / "legacy.db"
    original = legacy_database(path)
    engine = create_engine(URL.create("sqlite+pysqlite", database=str(path)))
    event.listen(engine, "connect", enable_sqlite_foreign_keys)
    try:
        backup = upgrade_project_metrics(engine)
        assert backup.exists()
        with sqlite3.connect(backup) as db:
            assert db.execute("SELECT * FROM experiment_results").fetchall() == original["experiment_results"]
        Base.metadata.create_all(engine)
        install_metric_constraints(engine)
        with engine.connect() as connection:
            for table in ["projects", "experiment_batches", "experiments"]:
                assert [tuple(row) for row in connection.exec_driver_sql(f"SELECT * FROM {table}")] == original[table]
            rows = connection.exec_driver_sql("SELECT id,experiment_id,accuracy,precision,recall,f1,loss,updated_at FROM experiment_results").all()
            assert [tuple(row) for row in rows] == original["experiment_results"]
            assert connection.exec_driver_sql("SELECT custom_metrics FROM experiment_results").scalar_one() == "{}"
            assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
            assert not connection.exec_driver_sql("PRAGMA foreign_key_check").all()
        assert upgrade_project_metrics(engine) is None
        assert len(list(tmp_path.glob("*.pre-project-metrics-*.db"))) == 1
    finally:
        engine.dispose()


def test_migration_failure_rolls_back_and_keeps_backup(tmp_path):
    path = tmp_path / "bad.db"
    original = legacy_database(path, bad_foreign_key=True)
    engine = create_engine(URL.create("sqlite+pysqlite", database=str(path)))
    event.listen(engine, "connect", enable_sqlite_foreign_keys)
    try:
        with pytest.raises(RuntimeError, match="Foreign key check failed"):
            upgrade_project_metrics(engine)
        with engine.connect() as connection:
            assert "custom_metrics" not in [row[1] for row in connection.exec_driver_sql("PRAGMA table_info(experiment_results)")]
            assert [tuple(row) for row in connection.exec_driver_sql("SELECT * FROM experiment_results")] == original["experiment_results"]
            assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
        assert len(list(tmp_path.glob("*.pre-project-metrics-*.db"))) == 1
    finally:
        engine.dispose()


def test_migration_rechecks_schema_after_acquiring_write_lock(tmp_path, monkeypatch):
    path = tmp_path / "racing-start.db"
    legacy_database(path)
    engine = create_engine(URL.create("sqlite+pysqlite", database=str(path)))
    event.listen(engine, "connect", enable_sqlite_foreign_keys)
    try:
        upgrade_project_metrics(engine)
        Base.metadata.create_all(engine)
        install_metric_constraints(engine)
        with engine.begin() as connection:
            connection.exec_driver_sql("INSERT INTO project_metrics (project_id,key,name,unit,direction) VALUES (8,'latency_ms','Latency','ms','min')")
            connection.exec_driver_sql("UPDATE experiment_results SET custom_metrics = ? WHERE id=21", ('{"latency_ms":13}',))
        original = Connection.exec_driver_sql
        stale_inspection = False
        def execute(connection, statement, *args, **kwargs):
            nonlocal stale_inspection
            if statement == "PRAGMA table_info(experiment_results)" and not stale_inspection:
                stale_inspection = True
                return SimpleNamespace(all=lambda: [(0, "id")])
            return original(connection, statement, *args, **kwargs)
        monkeypatch.setattr(Connection, "exec_driver_sql", execute)
        assert upgrade_project_metrics(engine) is None
        with engine.connect() as connection:
            assert connection.exec_driver_sql("SELECT custom_metrics FROM experiment_results WHERE id=21").scalar_one() == '{"latency_ms":13}'
            assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
    finally:
        engine.dispose()
