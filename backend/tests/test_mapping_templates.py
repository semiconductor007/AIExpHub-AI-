"""Templates are isolated, atomic, and never reconnect to a deleted metric by name."""

import sqlite3

import pytest
from sqlalchemy import URL, create_engine, event, text

from app.database import Base, enable_sqlite_foreign_keys
from app.migrations import backup_before_mapping_templates
from app.models import ResultMappingEntry, ResultMappingTemplate


def url(project):
    return f"/projects/{project['id']}/result-mapping-templates"


def mapping(key="accuracy", pointer="/evaluation/accuracy", metric_id=None, builtin=True):
    return {"metric_key": key, "pointer": pointer, "metric_id": metric_id, "builtin": builtin}


def test_crud_and_duplicate_names_are_project_local(client, sample_project):
    base = url(sample_project)
    created = client.post(base, json={"name": "  evaluation  ", "mappings": [mapping()]} )
    assert created.status_code == 201
    template = created.json()
    assert template["name"] == "evaluation"
    assert set(template) == {"id", "project_id", "name", "mappings"}
    assert client.get(base).json() == [template]
    assert client.post(base, json={"name": "evaluation", "mappings": [mapping()]}).status_code == 409
    other = client.post("/projects", json={"name": "other"}).json()
    assert client.post(url(other), json={"name": "evaluation", "mappings": [mapping()]}).status_code == 201
    endpoint = f"{base}/{template['id']}"
    assert client.patch(endpoint, json={"name": "renamed"}).json()["mappings"] == template["mappings"]
    changed = client.put(endpoint, json={"name": "renamed", "mappings": [mapping("loss", "/result/loss")]} )
    assert changed.status_code == 200
    assert changed.json()["mappings"] == [mapping("loss", "/result/loss")]
    # Updating the same metric key must not conflict with its previous entry.
    assert client.put(endpoint, json={"name": "renamed", "mappings": [mapping("loss", "/loss")]}).status_code == 200
    assert client.delete(endpoint).status_code == 204
    assert client.get(base).json() == []
    assert client.delete(endpoint).status_code == 404


@pytest.mark.parametrize("payload", [
    {"name": " ", "mappings": [mapping()]},
    {"name": None, "mappings": [mapping()]},
    {"mappings": [mapping()]},
    {"name": "x", "mappings": []},
    {"name": "x", "mappings": [mapping(), mapping()]},
    {"name": "x", "mappings": [mapping(pointer="$.accuracy")]},
    {"name": "x", "mappings": [mapping(pointer="/bad~2escape")]},
    {"name": "x", "mappings": [mapping(pointer="/a" * 101)]},
    {"name": "x", "mappings": [mapping(key="unknown")]},
    {"name": "x", "mappings": [mapping(metric_id=1)]},
    {"name": "x", "mappings": [mapping(key="latency", builtin=False)]},
    {"name": "x", "mappings": [mapping()], "values": {"accuracy": 0.8}},
])
def test_invalid_input_creates_no_template(client, sample_project, payload):
    assert client.post(url(sample_project), json=payload).status_code == 422
    assert client.get(url(sample_project)).json() == []


def test_foreign_resources_and_metric_identity(client, sample_project):
    other = client.post("/projects", json={"name": "other"}).json()
    metric = client.post(f"/projects/{other['id']}/metrics", json={"key": "latency", "name": "Latency", "direction": "min"}).json()
    assert client.post(url(sample_project), json={"name": "bad", "mappings": [mapping("latency", "/latency", metric["id"], False)]}).status_code == 422
    own = client.post(url(sample_project), json={"name": "ok", "mappings": [mapping()]}).json()
    for method, body in [("get", None), ("post", {"name": "x", "mappings": [mapping()]})]:
        response = getattr(client, method)("/projects/9999/result-mapping-templates", **({"json": body} if body else {}))
        assert response.status_code == 404
    foreign = f"{url(other)}/{own['id']}"
    assert client.patch(foreign, json={"name": "x"}).status_code == 404
    assert client.put(foreign, json={"name": "x", "mappings": [mapping()]}).status_code == 404
    assert client.delete(foreign).status_code == 404


def test_deleted_metric_stays_invalid_even_after_id_and_key_reuse(client, sample_project):
    metric_base = f"/projects/{sample_project['id']}/metrics"
    payload = {"key": "latency", "name": "Latency", "direction": "min"}
    metric = client.post(metric_base, json=payload).json()
    template = client.post(url(sample_project), json={"name": "test", "mappings": [mapping("latency", "/time", metric['id'], False), mapping()]}).json()
    assert client.delete(f"{metric_base}/{metric['id']}").status_code == 204
    recreated = client.post(metric_base, json=payload).json()
    assert recreated['id'] == metric['id']  # Existing SQLite metric table may reuse a highest ID.
    invalid = client.get(url(sample_project)).json()[0]
    assert invalid['mappings'][0]['metric_id'] is None
    assert invalid['mappings'][0]['builtin'] is False
    endpoint = f"{url(sample_project)}/{template['id']}"
    assert client.patch(endpoint, json={"name": "still invalid"}).status_code == 200
    # An explicit replacement is allowed, no automatic relinking took place.
    assert client.put(endpoint, json={"name": "fixed", "mappings": [mapping()]}).status_code == 200


def test_failed_replacement_rolls_back_and_project_delete_cascades(client, sample_project, db_session):
    base = url(sample_project)
    one = client.post(base, json={"name": "one", "mappings": [mapping()]}).json()
    client.post(base, json={"name": "two", "mappings": [mapping()]})
    assert client.put(f"{base}/{one['id']}", json={"name": "two", "mappings": [mapping("loss", "/loss")]}).status_code == 409
    assert client.get(base).json()[0] == one
    assert client.put(f"{base}/{one['id']}", json={"name": "one", "mappings": [mapping("removed", "/x", 999, False)]}).status_code == 422
    assert client.get(base).json()[0] == one
    assert client.delete(f"/projects/{sample_project['id']}").status_code == 204
    assert db_session.query(ResultMappingTemplate).count() == 0
    assert db_session.query(ResultMappingEntry).count() == 0


def test_additive_upgrade_backs_up_existing_rows_once(tmp_path):
    path = tmp_path / "existing.db"
    engine = create_engine(URL.create("sqlite+pysqlite", database=str(path)))
    event.listen(engine, "connect", enable_sqlite_foreign_keys)
    try:
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE projects (id INTEGER PRIMARY KEY, name TEXT NOT NULL, description TEXT, created_at DATETIME NOT NULL)"))
            connection.execute(text("INSERT INTO projects VALUES (7, 'keep', NULL, '2026-01-01')"))
        backup = backup_before_mapping_templates(engine)
        assert backup is not None and backup.exists()
        with sqlite3.connect(backup) as connection:
            assert connection.execute("SELECT name FROM projects").fetchall() == [("keep",)]
            assert not connection.execute("SELECT name FROM sqlite_master WHERE name='result_mapping_templates'").fetchall()
        Base.metadata.create_all(engine)
        assert backup_before_mapping_templates(engine) is None
        with engine.connect() as connection:
            assert connection.execute(text("SELECT name FROM projects")).all() == [("keep",)]
            assert not connection.exec_driver_sql("PRAGMA foreign_key_check").all()
    finally:
        engine.dispose()
