"""Read-only previews and all-or-nothing imports, isolated from user data."""

import json

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Experiment, ExperimentResult


def document(*rows, **metadata):
    return {"experiments": list(rows), **metadata}


def row(number="IMPORT-001", **changes):
    return {"experiment_no": number, "model_name": "Model", "parameters": {"seed": 42}, "result": {"accuracy": 0.8}, **changes}


def paths(batch):
    base = f"/batches/{batch['id']}/imports"
    return base + "/preview", base


def test_preview_read_only_and_atomic_success(client, sample_batch, db_session):
    preview, confirm = paths(sample_batch)
    payload = document(row(" import-001 "), row("IMPORT-002", result=None), row("IMPORT-003", result={"loss": 0}))
    response = client.post(preview, json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["can_import"] and data["valid_count"] == data["total"] == 3
    assert data["rows"][0]["normalized"]["experiment_no"] == "IMPORT-001"
    assert db_session.scalar(select(func.count()).select_from(Experiment)) == 0
    assert db_session.scalar(select(func.count()).select_from(ExperimentResult)) == 0
    saved = client.post(confirm, json=payload)
    assert saved.status_code == 201 and len(saved.json()) == 3
    assert [item["experiment_no"] for item in saved.json()] == ["IMPORT-001", "IMPORT-002", "IMPORT-003"]
    assert client.get(f"/experiments/{saved.json()[1]['id']}/result").status_code == 404
    assert client.get(f"/experiments/{saved.json()[2]['id']}/result").json()["loss"] == 0
    assert db_session.scalar(select(func.count()).select_from(ExperimentResult)) == 2
    assert client.post(confirm, json=payload).status_code == 422  # Retrying cannot duplicate or overwrite.
    assert db_session.scalar(select(func.count()).select_from(Experiment)) == 3


@pytest.mark.parametrize("bad", [
    row(model_name=" "), row(parameters={}), row(parameters=[]), row(result={}),
    row(result={"accuracy": None}), row(result={"accuracy": True}), row(result={"accuracy": "0.5"}),
    row(result={"accuracy": 1.1}), row(result={"loss": -1}), row(result={"unknown": 1}),
    row(result=[]), row(batch_id=999), 42, None,
])
def test_invalid_row_prevents_entire_import(client, sample_batch, db_session, bad):
    preview, confirm = paths(sample_batch)
    payload = document(row("GOOD-001"), bad)
    checked = client.post(preview, json=payload)
    assert checked.status_code == 200
    assert checked.json()["valid_count"] == 1 and not checked.json()["can_import"]
    assert checked.json()["rows"][1]["errors"]
    assert client.post(confirm, json=payload).status_code == 422
    assert db_session.scalar(select(func.count()).select_from(Experiment)) == 0


def test_global_duplicate_and_file_duplicate(client, sample_batch, sample_experiment):
    preview, confirm = paths(sample_batch)
    payload = document(row(" exp-001 "), row("NEW"), row(" new "))
    checked = client.post(preview, json=payload).json()
    assert checked["valid_count"] == 0
    assert "系统" in checked["rows"][0]["errors"][0]
    assert all("文件内" in item["errors"][0] for item in checked["rows"][1:])
    original = client.get(f"/experiments/{sample_experiment['id']}").json()
    assert client.post(confirm, json=payload).status_code == 422
    assert client.get(f"/experiments/{sample_experiment['id']}").json() == original


def test_confirm_rechecks_after_preview(client, sample_batch, experiment_payload, db_session):
    preview, confirm = paths(sample_batch)
    payload = document(row("LATER"), row("SAFE"))
    assert client.post(preview, json=payload).json()["can_import"]
    inserted = client.post(f"/batches/{sample_batch['id']}/experiments", json={**experiment_payload, "experiment_no": "LATER"}).json()
    assert client.post(confirm, json=payload).status_code == 422
    assert list(db_session.scalars(select(Experiment.id))) == [inserted["id"]]


def test_constraint_failure_rolls_back_rows_already_flushed(client, sample_batch, db_session, monkeypatch):
    original = Session.flush
    calls = []
    def conflicting(session, *args, **kwargs):
        calls.append(True)
        if len(calls) == 2:
            raise IntegrityError("INSERT", {}, Exception("simulated concurrent uniqueness conflict"))
        return original(session, *args, **kwargs)
    monkeypatch.setattr(Session, "flush", conflicting)
    response = client.post(paths(sample_batch)[1], json=document(row("FIRST"), row("SECOND")))
    assert response.status_code == 409
    assert db_session.scalar(select(func.count()).select_from(Experiment)) == 0
    assert db_session.scalar(select(func.count()).select_from(ExperimentResult)) == 0


@pytest.mark.parametrize("payload", [{"experiments": []}, {"experiments": [row()] * 101}, {"experiments": "bad"}, {"experiments": [row()], "format_version": 2}, {"experiments": [row()], "extra": True}])
def test_document_shape_and_limits(client, sample_batch, payload):
    assert client.post(paths(sample_batch)[0], json=payload).status_code == 422


@pytest.mark.parametrize("literal", ["NaN", "Infinity", "1e400"])
def test_nonfinite_rows_are_preview_errors(client, sample_batch, literal):
    payload = json.dumps(document(row())).replace('0.8', literal)
    response = client.post(paths(sample_batch)[0], content=payload, headers={"Content-Type": "application/json"})
    assert response.status_code == 200 and not response.json()["can_import"]
    nested = document(row(parameters={"nested": [float("inf")]}))
    response = client.post(paths(sample_batch)[0], content=json.dumps(nested), headers={"Content-Type": "application/json"})
    assert response.status_code == 200 and not response.json()["can_import"]


def test_template_custom_values_and_stale_definition(client, sample_project, sample_batch):
    metric_path = f"/projects/{sample_project['id']}/metrics"
    definition = {"key": "latency_ms", "name": "耗时", "unit": "ms", "direction": "min", "lower_bound": 0, "upper_bound": 100}
    metric = client.post(metric_path, json=definition).json()
    template_path = f"/projects/{sample_project['id']}/import-template"
    template = client.get(template_path)
    assert template.status_code == 200
    payload = template.json()
    assert len(payload["metric_definitions"]) == 6
    assert payload["experiments"][0]["result"]["latency_ms"] is None
    payload["experiments"] = [row(result={"latency_ms": 0})]
    preview, confirm = paths(sample_batch)
    assert client.post(preview, json=payload).json()["can_import"]
    assert client.put(metric_path + f"/{metric['id']}", json={**definition, "unit": "s"}).status_code == 200
    assert client.post(confirm, json=payload).status_code == 422
    payload = client.get(template_path).json()
    payload["experiments"] = [row(result={"latency_ms": 101})]
    assert not client.post(preview, json=payload).json()["can_import"]
    payload["experiments"] = [row(result={"latency_ms": 0})]
    imported = client.post(confirm, json=payload).json()
    result = client.get(f"/experiments/{imported[0]['id']}/result").json()
    assert result["custom_metrics"] == {"latency_ms": 0}


def test_project_and_resource_boundaries(client, sample_project, sample_batch):
    assert client.get("/projects/999999/import-template").status_code == 404
    assert client.post("/batches/999999/imports/preview", json=document(row())).status_code == 404
    assert client.post("/batches/999999/imports", json=document(row())).status_code == 404
    other = client.post("/projects", json={"name": "Other"}).json()
    payload = document(row(), project_id=other["id"])
    assert client.post(paths(sample_batch)[0], json=payload).status_code == 422
    assert client.post(paths(sample_batch)[1], json=payload).status_code == 422


def test_preview_has_no_commit(client, sample_batch, test_engine):
    from sqlalchemy import event
    commits = []
    def record(connection): commits.append(True)
    event.listen(test_engine, "commit", record)
    try:
        assert client.post(paths(sample_batch)[0], json=document(row())).json()["can_import"]
    finally:
        event.remove(test_engine, "commit", record)
    assert not commits


def test_maximum_batch_and_comparison_use_imported_values(client, sample_batch, db_session):
    payload = document(*(row(f"BULK-{index}", result={"accuracy": index / 100}) for index in range(100)))
    preview, confirm = paths(sample_batch)
    assert client.post(preview, json=payload).json()["valid_count"] == 100
    created = client.post(confirm, json=payload)
    assert created.status_code == 201 and len(created.json()) == 100
    first, last = created.json()[0], created.json()[-1]
    comparison = client.post('/experiments/compare', json={'experiment_ids': [first['id'], last['id']]})
    assert comparison.json()['best_by_metric']['accuracy'] == {'direction':'max','value':0.99,'experiment_ids':[last['id']]}
    assert db_session.scalar(select(func.count()).select_from(ExperimentResult)) == 100
