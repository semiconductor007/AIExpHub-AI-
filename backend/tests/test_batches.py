import pytest

from app.models import ExperimentBatch


def test_batch_creation_scoped_ordered_list_and_delete(client, sample_project, db_session):
    path = f"/projects/{sample_project['id']}/batches"
    response = client.get(path)
    assert response.status_code == 200 and response.json() == []
    created = []
    for name in ("  Same batch  ", "Same batch"):
        response = client.post(path, json={"name": name})
        assert response.status_code == 201
        batch = response.json()
        assert set(batch) == {"id", "project_id", "name", "description", "created_at"}
        assert batch["project_id"] == sample_project["id"] and batch["name"] == "Same batch"
        created.append(batch)
    other = client.post("/projects", json={"name": "Other project"})
    assert other.status_code == 201
    other_batch = client.post(f"/projects/{other.json()['id']}/batches", json={"name": "Other batch"})
    assert other_batch.status_code == 201
    response = client.get(path)
    assert response.status_code == 200 and response.json() == created
    assert [b["id"] for b in created] == sorted(b["id"] for b in created)
    assert db_session.get(ExperimentBatch, created[0]["id"]).project_id == sample_project["id"]
    response = client.delete(f"/batches/{created[0]['id']}")
    assert response.status_code == 204 and response.content == b""
    assert client.get(f"/batches/{created[0]['id']}").status_code == 404
    db_session.expire_all()
    assert db_session.get(ExperimentBatch, created[0]["id"]) is None


def test_batch_missing_parent_and_resources(client):
    for method in ("get", "post"):
        kwargs = {"json": {"name": "batch"}} if method == "post" else {}
        response = getattr(client, method)("/projects/999999/batches", **kwargs)
        assert response.status_code == 404 and response.json() == {"detail": "Project not found"}
    for method in ("get", "put", "delete"):
        kwargs = {"json": {"name": "batch"}} if method == "put" else {}
        response = getattr(client, method)("/batches/999999", **kwargs)
        assert response.status_code == 404
        assert response.json() == {"detail": "Experiment batch not found"}


@pytest.mark.parametrize("body", [{"name": "   "}, {"name": 123}, {"name": "batch", "project_id": 42}])
def test_batch_invalid_input(client, sample_project, body):
    path = f"/projects/{sample_project['id']}/batches"
    response = client.post(path, json=body)
    assert response.status_code == 422 and isinstance(response.json()["detail"], list)
    assert client.get(path).json() == []


def test_batch_put_preserves_parent_and_rejects_migration(client, sample_batch, db_session):
    path = f"/batches/{sample_batch['id']}"
    response = client.put(path, json={"name": "  updated  ", "description": "new"})
    assert response.status_code == 200
    updated = response.json()
    assert updated["name"] == "updated" and updated["description"] == "new"
    assert updated["project_id"] == sample_batch["project_id"]
    assert updated["created_at"] == sample_batch["created_at"]
    assert client.get(path).json() == updated
    for body in ({"name": "wrong", "project_id": sample_batch["project_id"] + 100}, {"description": "missing name"}):
        response = client.put(path, json=body)
        assert response.status_code == 422
        assert client.get(path).json() == updated
    response = client.put(path, json={"name": "final", "description": None})
    assert response.status_code == 200 and response.json()["description"] is None
    stored = db_session.get(ExperimentBatch, sample_batch["id"])
    assert stored.name == "final" and stored.project_id == sample_batch["project_id"]


def test_batch_delete_restrict_preserves_experiment(client, sample_experiment, sample_batch):
    response = client.delete(f"/batches/{sample_batch['id']}")
    assert response.status_code == 409
    assert response.json() == {"detail": "Experiment batch has existing experiments"}
    assert client.get(f"/batches/{sample_batch['id']}").json() == sample_batch
    assert client.get(f"/experiments/{sample_experiment['id']}").json() == sample_experiment
