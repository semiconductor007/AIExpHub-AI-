from datetime import datetime

import pytest

from app.models import Project


def test_project_creation_duplicate_names_list_and_delete(client, db_session):
    response = client.get("/projects")
    assert response.status_code == 200
    assert response.json() == []
    created = []
    for name in ("  Same project  ", "Same project"):
        response = client.post("/projects", json={"name": name})
        assert response.status_code == 201
        project = response.json()
        assert set(project) == {"id", "name", "description", "created_at"}
        assert project["name"] == "Same project" and project["description"] is None
        datetime.fromisoformat(project["created_at"])
        assert db_session.get(Project, project["id"]).name == "Same project"
        created.append(project)
    assert created[0]["id"] != created[1]["id"]
    response = client.get("/projects")
    assert response.status_code == 200 and response.json() == created
    assert [p["id"] for p in created] == sorted(p["id"] for p in created)
    response = client.delete(f"/projects/{created[0]['id']}")
    assert response.status_code == 204 and response.content == b""
    assert client.get(f"/projects/{created[0]['id']}").status_code == 404
    db_session.expire_all()
    assert db_session.get(Project, created[0]["id"]) is None


@pytest.mark.parametrize("body", [{"name": "   "}, {"name": 123}, {"name": "valid", "id": 42}])
def test_project_invalid_create_input(client, body):
    response = client.post("/projects", json=body)
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)
    assert client.get("/projects").json() == []


def test_project_missing_resources(client):
    for method in ("get", "put", "delete"):
        kwargs = {"json": {"name": "updated"}} if method == "put" else {}
        response = getattr(client, method)("/projects/999999", **kwargs)
        assert response.status_code == 404
        assert response.json() == {"detail": "Project not found"}


@pytest.mark.parametrize("clear_body", [{"name": "final"}, {"name": "final", "description": None}])
def test_project_put_and_description_clear(client, sample_project, db_session, clear_body):
    path = f"/projects/{sample_project['id']}"
    response = client.put(path, json={"name": "  updated  ", "description": "new description"})
    assert response.status_code == 200
    assert response.json()["name"] == "updated"
    assert response.json()["description"] == "new description"
    assert response.json()["created_at"] == sample_project["created_at"]
    response = client.put(path, json=clear_body)
    assert response.status_code == 200 and response.json()["description"] is None
    assert client.get(path).json() == response.json()
    stored = db_session.get(Project, sample_project["id"])
    assert stored.name == "final" and stored.description is None


def test_project_put_requires_name(client, sample_project):
    path = f"/projects/{sample_project['id']}"
    response = client.put(path, json={"description": "must not save"})
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)
    assert client.get(path).json() == sample_project


def test_project_delete_restrict_preserves_batch(client, sample_batch, sample_project):
    response = client.delete(f"/projects/{sample_project['id']}")
    assert response.status_code == 409
    assert response.json() == {"detail": "Project has existing batches"}
    assert client.get(f"/projects/{sample_project['id']}").json() == sample_project
    assert client.get(f"/batches/{sample_batch['id']}").json() == sample_batch
