import json
from datetime import datetime

import pytest
from sqlalchemy import select

from app.models import ExperimentResult


METRICS = ("accuracy", "precision", "recall", "f1", "loss")


def test_result_missing_resources_and_put_not_upsert(client, sample_experiment, db_session):
    path = f"/experiments/{sample_experiment['id']}/result"
    for method in ("get", "put"):
        kwargs = {"json": {"loss": 0}} if method == "put" else {}
        response = getattr(client, method)(path, **kwargs)
        assert response.status_code == 404
        assert response.json() == {"detail": "Experiment result not found"}
    assert db_session.scalar(select(ExperimentResult.id)) is None
    for method in ("get", "post", "put"):
        kwargs = {"json": {"loss": 0}} if method != "get" else {}
        response = getattr(client, method)("/experiments/999999/result", **kwargs)
        assert response.status_code == 404 and response.json() == {"detail": "Experiment not found"}


def test_result_create_read_and_duplicate(client, sample_experiment, db_session):
    path = f"/experiments/{sample_experiment['id']}/result"
    response = client.post(path, json={"accuracy": 0.8})
    assert response.status_code == 201
    result = response.json()
    assert set(result) == {"id", "experiment_id", *METRICS, "updated_at"}
    assert result["experiment_id"] == sample_experiment["id"] and result["accuracy"] == 0.8
    assert all(result[field] is None for field in METRICS[1:])
    datetime.fromisoformat(result["updated_at"])
    response = client.get(path)
    assert response.status_code == 200 and response.json() == result
    response = client.post(path, json={"loss": 0.2})
    assert response.status_code == 409
    assert response.json() == {"detail": "Experiment result already exists"}
    assert client.get(path).json() == result
    stored = db_session.get(ExperimentResult, result["id"])
    assert stored.accuracy == 0.8 and stored.loss is None
    assert len(list(db_session.scalars(select(ExperimentResult)))) == 1


@pytest.mark.parametrize(
    "body",
    [{"accuracy": 0}, {"accuracy": 1}, {"f1": 0}, {"f1": 1}, {"loss": 0}, {"loss": 2.5}, {"accuracy": None, "loss": 0.5}],
)
def test_result_valid_boundaries_and_partial_null(client, sample_experiment, db_session, body):
    path = f"/experiments/{sample_experiment['id']}/result"
    response = client.post(path, json=body)
    assert response.status_code == 201
    result = response.json()
    for field in METRICS:
        assert result[field] == body.get(field)
    assert client.get(path).json() == result
    stored = db_session.get(ExperimentResult, result["id"])
    assert all(getattr(stored, field) == body.get(field) for field in METRICS)


@pytest.mark.parametrize("method", ["post", "put"])
def test_result_invalid_inputs_preserve_state(client, sample_experiment, db_session, method):
    path = f"/experiments/{sample_experiment['id']}/result"
    original = None
    if method == "put":
        response = client.post(path, json={"accuracy": 0.8, "f1": 0.7})
        assert response.status_code == 201
        original = response.json()
    invalid_bodies = [{}, {field: None for field in METRICS}, {"accuracy": 0.5, "loss": -1}]
    for field in METRICS:
        invalid_bodies += [{field: value} for value in (True, False, "0.8", "1", "abc", [], {})]
        invalid_bodies.append({field: -0.01})
        if field != "loss":
            invalid_bodies.append({field: 1.01})
    invalid_bodies += [{"loss": 0, field: value} for field, value in (("id", 42), ("experiment_id", sample_experiment["id"]), ("updated_at", "2026-01-01"), ("experiment", {}), ("result", {}), ("extra", "value"))]
    for body in invalid_bodies:
        response = getattr(client, method)(path, json=body)
        assert response.status_code == 422, body
        assert isinstance(response.json()["detail"], list) and response.json()["detail"]
    response = client.get(path)
    if original is None:
        assert response.status_code == 404
        assert db_session.scalar(select(ExperimentResult.id)) is None
    else:
        assert response.status_code == 200 and response.json() == original
        stored = db_session.get(ExperimentResult, original["id"])
        assert stored.accuracy == 0.8 and stored.f1 == 0.7


@pytest.mark.parametrize("literal", ["NaN", "Infinity", "-Infinity"])
def test_result_nonfinite_http_input_rejected(client, sample_experiment, db_session, literal):
    path = f"/experiments/{sample_experiment['id']}/result"

    def invalid_constant(value):
        pytest.fail(f"Error response contains a nonstandard numeric literal: {value}")

    for field in METRICS:
        response = client.post(path, content='{"' + field + '":' + literal + '}', headers={"Content-Type": "application/json"})
        assert response.status_code == 422
        error = json.loads(response.text, parse_constant=invalid_constant)
        assert isinstance(error["detail"], list)
        assert error["detail"][0]["type"] == "finite_number"
        assert isinstance(error["detail"][0]["input"], str)
        assert db_session.scalar(select(ExperimentResult.id)) is None
    assert client.get(path).status_code == 404
    ordinary = client.post(path, json={"accuracy": 1.5})
    assert ordinary.status_code == 422
    assert isinstance(ordinary.json()["detail"], list)
    assert ordinary.json()["detail"][0]["type"] == "less_than_equal"
    created = client.post(path, json={"loss": 0})
    assert created.status_code == 201
    response = client.put(path, content='{"loss":' + literal + '}', headers={"Content-Type": "application/json"})
    assert response.status_code == 422
    json.loads(response.text, parse_constant=invalid_constant)
    assert client.get(path).json() == created.json()


def test_result_put_replaces_metrics_preserves_ids_and_updates_time(client, sample_experiment, db_session):
    path = f"/experiments/{sample_experiment['id']}/result"
    response = client.post(path, json={"accuracy": 0.8, "f1": 0.7})
    assert response.status_code == 201
    original = response.json()
    response = client.put(path, json={"accuracy": 0.9})
    assert response.status_code == 200
    updated = response.json()
    assert updated["id"] == original["id"] and updated["experiment_id"] == original["experiment_id"]
    assert updated["accuracy"] == 0.9 and all(updated[f] is None for f in METRICS[1:])
    assert datetime.fromisoformat(updated["updated_at"]) >= datetime.fromisoformat(original["updated_at"])
    assert client.get(path).json() == updated
    stored = db_session.get(ExperimentResult, original["id"])
    assert stored.accuracy == 0.9 and stored.f1 is None


def test_experiment_delete_cascades_result_over_http(client, sample_experiment, db_session):
    path = f"/experiments/{sample_experiment['id']}"
    created = client.post(path + "/result", json={"loss": 0})
    assert created.status_code == 201
    response = client.delete(path)
    assert response.status_code == 204 and response.content == b""
    response = client.get(path + "/result")
    assert response.status_code == 404 and response.json() == {"detail": "Experiment not found"}
    assert db_session.get(ExperimentResult, created.json()["id"]) is None


def test_swagger_contains_only_current_endpoints(client):
    response = client.get("/docs")
    assert response.status_code == 200 and "Swagger UI" in response.text
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    assert len(paths) == 8 and sum(len(methods) for methods in paths.values()) == 19
    assert set(paths["/experiments/{experiment_id}/result"]) == {"post", "get", "put"}
    tags = {tag for methods in paths.values() for operation in methods.values() for tag in operation["tags"]}
    assert tags == {"Health", "Projects", "Experiment Batches", "Experiments", "Experiment Results"}
