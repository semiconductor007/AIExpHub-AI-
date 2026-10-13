"""Shared definitions, strict values, compatibility and read-only comparison."""

import json

import pytest
from sqlalchemy import event, select
from sqlalchemy.exc import IntegrityError

from app.models import ExperimentResult, ProjectMetric


@pytest.fixture
def metric(client, sample_project):
    body = {"key": "latency_ms", "name": "推理耗时", "unit": "ms", "direction": "min", "lower_bound": 0, "upper_bound": 100}
    response = client.post(f"/projects/{sample_project['id']}/metrics", json=body)
    assert response.status_code == 201
    return response.json()


def test_definitions_scoped_unique_and_defaults(client, sample_project, metric):
    path = f"/projects/{sample_project['id']}/metrics"
    definitions = client.get(path).json()
    assert len(definitions) == 6 and all(item["builtin"] for item in definitions[:5])
    assert definitions[-1] == metric
    body = {k: metric[k] for k in ("key", "name", "unit", "direction", "lower_bound", "upper_bound")}
    assert client.post(path, json={**body, "key": " LATENCY_MS "}).status_code == 409
    other = client.post("/projects", json={"name": "Other"}).json()
    assert client.post(f"/projects/{other['id']}/metrics", json=body).status_code == 201
    assert client.get("/projects/999999/metrics").status_code == 404
    assert client.delete(f"/projects/{other['id']}/metrics/{metric['id']}").status_code == 404
    assert client.put(path + f"/{metric['id']}", json={**body, "name": "延迟"}).status_code == 200


@pytest.mark.parametrize("changes", [
    {"key": "accuracy"}, {"key": "custom_metrics"}, {"key": "constructor"}, {"key": "a.b"}, {"key": ""},
    {"name": "   "}, {"direction": "up"}, {"lower_bound": True}, {"upper_bound": "10"},
    {"lower_bound": 10, "upper_bound": 1}, {"extra": 1},
])
def test_invalid_definition(client, sample_project, changes):
    body = {"key": "score", "name": "评分", "unit": "分", "direction": "max", **changes}
    assert client.post(f"/projects/{sample_project['id']}/metrics", json=body).status_code == 422


@pytest.mark.parametrize("custom", [[], None, "bad", {"latency_ms": True}, {"latency_ms": "1"}, {"latency_ms": -1}, {"latency_ms": 101}, {"unknown": 1}, {"unknown": None}])
def test_invalid_values_preserve_result(client, sample_experiment, metric, custom):
    path = f"/experiments/{sample_experiment['id']}/result"
    original = client.post(path, json={"accuracy": 0.8, "custom_metrics": {"latency_ms": 10}}).json()
    assert client.put(path, json={"custom_metrics": custom}).status_code == 422
    assert client.get(path).json() == original


@pytest.mark.parametrize("literal", ["NaN", "Infinity", "-Infinity", "1e400"])
def test_custom_nonfinite(client, sample_experiment, metric, literal):
    response = client.post(f"/experiments/{sample_experiment['id']}/result", content='{"custom_metrics":{"latency_ms":'+literal+'}}', headers={"Content-Type": "application/json"})
    assert response.status_code == 422
    json.loads(response.text, parse_constant=lambda value: pytest.fail("nonstandard error JSON"))


def test_custom_only_put_clear_and_used_definition(client, sample_project, sample_experiment, metric):
    path = f"/experiments/{sample_experiment['id']}/result"
    assert client.post(path, json={"custom_metrics": {"latency_ms": None}}).status_code == 422
    created = client.post(path, json={"custom_metrics": {"latency_ms": 0}})
    assert created.status_code == 201 and created.json()["accuracy"] is None
    metric_path = f"/projects/{sample_project['id']}/metrics/{metric['id']}"
    assert client.delete(metric_path).status_code == 409
    body = {k: metric[k] for k in ("key", "name", "unit", "direction", "lower_bound", "upper_bound")}
    for field, value in [("key", "other"), ("unit", "s"), ("direction", "max"), ("lower_bound", -1), ("upper_bound", 200)]:
        assert client.put(metric_path, json={**body, field: value}).status_code == 409
    assert client.put(metric_path, json={**body, "name": "延迟"}).status_code == 200
    updated = client.put(path, json={"loss": 0})
    assert updated.status_code == 200 and updated.json()["id"] == created.json()["id"]
    assert "custom_metrics" not in updated.json()
    assert client.delete(metric_path).status_code == 204


def test_custom_comparison_single_select_and_project_boundaries(client, sample_project, sample_experiment, sample_batch, experiment_payload, metric, test_engine):
    second = client.post(f"/batches/{sample_batch['id']}/experiments", json={**experiment_payload, "experiment_no": "EXP-002"}).json()
    other_project = client.post("/projects", json={"name": "Other"}).json()
    other_batch = client.post(f"/projects/{other_project['id']}/batches", json={"name": "Other"}).json()
    third = client.post(f"/batches/{other_batch['id']}/experiments", json={**experiment_payload, "experiment_no": "EXP-003"}).json()
    # Same key has a different unit/direction: it must remain a separate column.
    other_metric = client.post(f"/projects/{other_project['id']}/metrics", json={"key": "latency_ms", "name": "Other score", "unit": "分", "direction": "max"}).json()
    for experiment, value in [(sample_experiment, 10), (second, 10), (third, 80)]:
        assert client.post(f"/experiments/{experiment['id']}/result", json={"custom_metrics": {"latency_ms": value}}).status_code == 201
    ids = [second["id"], third["id"], sample_experiment["id"]]
    statements, commits = [], []
    def capture(conn, cursor, statement, parameters, context, many): statements.append(statement)
    def committed(conn): commits.append(True)
    event.listen(test_engine, "before_cursor_execute", capture)
    event.listen(test_engine, "commit", committed)
    try:
        response = client.post("/experiments/compare", json={"experiment_ids": ids})
    finally:
        event.remove(test_engine, "before_cursor_execute", capture)
        event.remove(test_engine, "commit", committed)
    assert response.status_code == 200 and len(statements) == 1 and not commits
    entries = response.json()["custom_metrics"]
    own = next(item for item in entries if item["definition"]["id"] == metric["id"])
    assert own["values"][str(third["id"])] is None
    assert own["best"] == {"direction": "min", "value": 10, "experiment_ids": [ids[0], ids[2]]}
    assert next(item for item in entries if item["definition"]["id"] == other_metric["id"])["best"]["experiment_ids"] == [third["id"]]
    client.put(f"/experiments/{sample_experiment['id']}/result", json={"custom_metrics": {"latency_ms": 0}})
    after = client.post("/experiments/compare", json={"experiment_ids": ids}).json()
    assert after["custom_metrics"][0]["best"]["experiment_ids"] == [sample_experiment["id"]]


def test_new_definition_has_null_old_values_and_unbounded_negative(client, sample_project, sample_experiment, sample_batch, experiment_payload):
    client.post(f"/experiments/{sample_experiment['id']}/result", json={"accuracy": 1})
    metric = client.post(f"/projects/{sample_project['id']}/metrics", json={"key": "delta", "name": "变化", "direction": "max"}).json()
    second = client.post(f"/batches/{sample_batch['id']}/experiments", json={**experiment_payload, "experiment_no": "EXP-002"}).json()
    empty = client.post("/experiments/compare", json={"experiment_ids": [sample_experiment['id'], second['id']]}).json()["custom_metrics"][0]
    assert empty["best"]["value"] is None and not empty["best"]["experiment_ids"]
    assert all(value is None for value in empty["values"].values())
    assert client.post(f"/experiments/{second['id']}/result", json={"custom_metrics": {"delta": -2}}).status_code == 201


@pytest.mark.parametrize("values", [{"latency_ms": None}, {"latency_ms": True}, {"latency_ms": -1}, {"latency_ms": 101}, {"unknown": 1}])
def test_database_custom_value_guards(db_session, sample_experiment, metric, values):
    db_session.add(ExperimentResult(experiment_id=sample_experiment["id"], custom_metrics=values))
    with pytest.raises(IntegrityError): db_session.commit()
    db_session.rollback()
    assert db_session.scalar(select(ExperimentResult.id)) is None


def test_database_definition_guard_and_experiment_cascade(db_session, client, sample_experiment, metric):
    created = client.post(f"/experiments/{sample_experiment['id']}/result", json={"custom_metrics": {"latency_ms": 10}}).json()
    definition = db_session.get(ProjectMetric, metric["id"])
    definition.direction = "max"
    with pytest.raises(IntegrityError): db_session.commit()
    db_session.rollback()
    db_session.delete(db_session.get(ProjectMetric, metric["id"]))
    with pytest.raises(IntegrityError): db_session.commit()
    db_session.rollback()
    assert client.delete(f"/experiments/{sample_experiment['id']}").status_code == 204
    assert db_session.get(ExperimentResult, created["id"]) is None
