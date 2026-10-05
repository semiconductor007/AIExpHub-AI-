from datetime import datetime

import pytest

from app.models import Experiment


def test_experiment_creation_normalization_scoped_list(client, sample_batch, experiment_payload, db_session):
    path = f"/batches/{sample_batch['id']}/experiments"
    response = client.get(path)
    assert response.status_code == 200 and response.json() == []
    created = []
    for number, parameters in ((" exp-001 ", {"temperature": 0.7}), ("custom id/42", {"nested": {"seed": 42}})):
        body = {**experiment_payload, "experiment_no": number, "model_name": "  Janus-Pro-1B  ", "parameters": parameters}
        response = client.post(path, json=body)
        assert response.status_code == 201
        experiment = response.json()
        assert set(experiment) == {"id", "batch_id", "experiment_no", "model_name", "parameters", "created_at", "notes"}
        assert experiment["experiment_no"] == number.strip().upper()
        assert experiment["model_name"] == "Janus-Pro-1B" and experiment["parameters"] == parameters
        assert experiment["batch_id"] == sample_batch["id"]
        datetime.fromisoformat(experiment["created_at"])
        assert client.get(f"/experiments/{experiment['id']}").json() == experiment
        stored = db_session.get(Experiment, experiment["id"])
        assert stored.experiment_no == experiment["experiment_no"]
        assert stored.parameters == parameters and stored.result is None
        created.append(experiment)
    other = client.post(f"/projects/{sample_batch['project_id']}/batches", json={"name": "Other batch"})
    assert other.status_code == 201
    outside = client.post(f"/batches/{other.json()['id']}/experiments", json={**experiment_payload, "experiment_no": "OUTSIDE"})
    assert outside.status_code == 201
    response = client.get(path)
    assert response.status_code == 200 and response.json() == created
    assert [e["id"] for e in created] == sorted(e["id"] for e in created)


def test_experiment_missing_parent_and_resources(client, experiment_payload):
    for method in ("get", "post"):
        kwargs = {"json": experiment_payload} if method == "post" else {}
        response = getattr(client, method)("/batches/999999/experiments", **kwargs)
        assert response.status_code == 404
        assert response.json() == {"detail": "Experiment batch not found"}
    for method in ("get", "put", "delete"):
        kwargs = {"json": experiment_payload} if method == "put" else {}
        response = getattr(client, method)("/experiments/999999", **kwargs)
        assert response.status_code == 404 and response.json() == {"detail": "Experiment not found"}


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("experiment_no", "   "),
        ("model_name", "   "),
        pytest.param("parameters", ..., id="parameters-missing"),
        ("parameters", {}),
        ("parameters", None),
        ("parameters", []),
        ("parameters", "abc"),
        ("parameters", 1),
    ],
)
def test_experiment_invalid_input(client, sample_experiment, experiment_payload, field, value):
    body = experiment_payload.copy()
    if value is ...:
        body.pop(field)
    else:
        body[field] = value
    path = f"/experiments/{sample_experiment['id']}"
    for method, target in (("post", f"/batches/{sample_experiment['batch_id']}/experiments"), ("put", path)):
        response = getattr(client, method)(target, json=body)
        assert response.status_code == 422 and isinstance(response.json()["detail"], list)
        assert client.get(path).json() == sample_experiment
    assert client.get(f"/batches/{sample_experiment['batch_id']}/experiments").json() == [sample_experiment]


@pytest.mark.parametrize("scope", ["same-batch", "other-batch", "other-project"])
def test_experiment_number_globally_unique(client, sample_experiment, sample_batch, experiment_payload, scope):
    batch_id = sample_batch["id"]
    if scope != "same-batch":
        project_id = sample_batch["project_id"]
        if scope == "other-project":
            response = client.post("/projects", json={"name": "Other project"})
            assert response.status_code == 201
            project_id = response.json()["id"]
        response = client.post(f"/projects/{project_id}/batches", json={"name": "Other batch"})
        assert response.status_code == 201
        batch_id = response.json()["id"]
    for number in ("EXP-001", " exp-001 "):
        response = client.post(f"/batches/{batch_id}/experiments", json={**experiment_payload, "experiment_no": number})
        assert response.status_code == 409
        assert response.json() == {"detail": "Experiment number already exists"}
    expected = [sample_experiment] if scope == "same-batch" else []
    assert client.get(f"/batches/{batch_id}/experiments").json() == expected
    assert client.get(f"/experiments/{sample_experiment['id']}").json() == sample_experiment


def test_experiment_put_full_update_and_own_number(client, sample_experiment, experiment_payload, db_session):
    path = f"/experiments/{sample_experiment['id']}"
    response = client.put(path, json={**experiment_payload, "experiment_no": " exp-001 "})
    assert response.status_code == 200 and response.json()["experiment_no"] == "EXP-001"
    body = {"experiment_no": " updated-id ", "model_name": "  Other model  ", "parameters": {"seed": 7}, "notes": "new notes"}
    response = client.put(path, json=body)
    assert response.status_code == 200
    updated = response.json()
    assert updated["experiment_no"] == "UPDATED-ID" and updated["model_name"] == "Other model"
    assert updated["parameters"] == {"seed": 7} and updated["notes"] == "new notes"
    assert updated["created_at"] == sample_experiment["created_at"]
    assert updated["batch_id"] == sample_experiment["batch_id"]
    assert client.get(path).json() == updated
    for missing_field in ("experiment_no", "model_name", "parameters"):
        invalid = body.copy()
        invalid.pop(missing_field)
        assert client.put(path, json=invalid).status_code == 422
        assert client.get(path).json() == updated
    body.pop("notes")
    response = client.put(path, json=body)
    assert response.status_code == 200 and response.json()["notes"] is None
    assert client.put(path, json={**body, "notes": None}).json()["notes"] is None
    stored = db_session.get(Experiment, sample_experiment["id"])
    assert stored.experiment_no == "UPDATED-ID" and stored.notes is None


def test_experiment_put_conflict_and_protected_fields_preserve_data(client, sample_experiment, experiment_payload):
    response = client.post(f"/batches/{sample_experiment['batch_id']}/experiments", json={**experiment_payload, "experiment_no": "EXP-002"})
    assert response.status_code == 201
    second = response.json()
    path = f"/experiments/{second['id']}"
    response = client.put(path, json={**experiment_payload, "experiment_no": " exp-001 ", "notes": "must not save"})
    assert response.status_code == 409
    assert response.json() == {"detail": "Experiment number already exists"}
    assert client.get(path).json() == second
    for field, value in (("batch_id", sample_experiment["batch_id"] + 100), ("id", 42), ("created_at", "2026-01-01"), ("project_id", 42), ("result", {})):
        response = client.put(path, json={**experiment_payload, "experiment_no": "EXP-002", field: value})
        assert response.status_code == 422
        assert client.get(path).json() == second


def test_experiment_delete(client, sample_experiment, db_session):
    path = f"/experiments/{sample_experiment['id']}"
    response = client.delete(path)
    assert response.status_code == 204 and response.content == b""
    response = client.get(path)
    assert response.status_code == 404 and response.json() == {"detail": "Experiment not found"}
    assert db_session.get(Experiment, sample_experiment["id"]) is None
