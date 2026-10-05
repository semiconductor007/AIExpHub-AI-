import sqlite3

from sqlalchemy import event
from sqlalchemy.exc import OperationalError


def test_health_executes_select_on_test_database(client, test_engine, tmp_path):
    statements = []

    def record(connection, cursor, statement, parameters, context, executemany):
        assert connection.engine is test_engine
        assert connection.engine.url.database == str(tmp_path / "test.db")
        statements.append(statement)

    event.listen(test_engine, "before_cursor_execute", record)
    try:
        response = client.get("/health")
    finally:
        event.remove(test_engine, "before_cursor_execute", record)
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "AIExpHub API"}
    assert "SELECT 1" in statements


def test_health_database_unavailable(client, test_engine):
    def unavailable(connection, cursor, statement, parameters, context, executemany):
        raise OperationalError(statement, parameters, sqlite3.OperationalError("test failure"))

    event.listen(test_engine, "before_cursor_execute", unavailable)
    try:
        response = client.get("/health")
    finally:
        event.remove(test_engine, "before_cursor_execute", unavailable)
    assert response.status_code == 503
    assert response.json() == {"detail": "Database connection unavailable"}
