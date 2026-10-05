"""Comparison API acceptance tests, using only isolated temporary SQLite files."""

import pytest
from sqlalchemy import event


METRICS = ("accuracy", "precision", "recall", "f1", "loss")


@pytest.fixture
def comparison_data(client, sample_experiment, sample_batch, experiment_payload):
    project_a = sample_batch["project_id"]
    batch_b = client.post(f"/projects/{project_a}/batches", json={"name": "Batch B"})
    assert batch_b.status_code == 201
    project_b = client.post("/projects", json={"name": "Project B"})
    assert project_b.status_code == 201
    batch_c = client.post(
        f"/projects/{project_b.json()['id']}/batches", json={"name": "Batch C"}
    )
    assert batch_c.status_code == 201
    experiments = [sample_experiment]
    for number, batch in enumerate([batch_b.json(), batch_c.json(), batch_c.json()], 2):
        response = client.post(
            f"/batches/{batch['id']}/experiments",
            json={**experiment_payload, "experiment_no": f"EXP-{number:03}",
                  "model_name": f"Model {number}"},
        )
        assert response.status_code == 201
        experiments.append(response.json())
    results = [
        {"accuracy": 0.7, "precision": 0.8, "recall": 0.6, "f1": 0.5, "loss": 0.4},
        {"accuracy": 0.8, "precision": 0.8, "recall": 0.4, "f1": 0.9, "loss": 0.2},
        {"accuracy": 0.75, "recall": 0.9},
    ]
    for experiment, result in zip(experiments, results):
        response = client.post(f"/experiments/{experiment['id']}/result", json=result)
        assert response.status_code == 201
    return {"experiments": experiments, "project_ids": [project_a, project_a,
            project_b.json()["id"], project_b.json()["id"]]}


@pytest.mark.parametrize("payload", [
    {}, {"experiment_ids": None}, {"experiment_ids": []}, {"experiment_ids": [1]},
    {"experiment_ids": [1, 1]}, {"experiment_ids": [0, 1]},
    {"experiment_ids": [-1, 2]}, {"experiment_ids": [True, 2]},
    {"experiment_ids": ["1", 2]}, {"experiment_ids": [1.0, 2]},
    {"experiment_ids": "1,2"}, {"experiment_ids": {"1": 1, "2": 2}},
    {"experiment_ids": [None, 2]}, {"experiment_ids": [[1], 2]},
    {"experiment_ids": [1, 2], "extra": "forbidden"},
])
def test_invalid_comparison_request(client, payload):
    response = client.post("/experiments/compare", json=payload)
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)


@pytest.mark.parametrize("missing_ids", [[999999], [888888, 999999], [999999, 888888]])
def test_missing_experiment_reports_first_missing_input(client, sample_experiment, missing_ids):
    response = client.post("/experiments/compare", json={
        "experiment_ids": [sample_experiment["id"], *missing_ids],
    })
    assert response.status_code == 404
    assert response.json() == {"detail": f"Experiment not found: {missing_ids[0]}"}


@pytest.mark.parametrize("second_index", [1, 2])
def test_cross_batch_and_project_comparison(client, comparison_data, second_index):
    experiments = comparison_data["experiments"]
    selected = [experiments[0], experiments[second_index]]
    assert selected[0]["batch_id"] != selected[1]["batch_id"]
    assert selected[0]["model_name"] != selected[1]["model_name"]
    if second_index == 2:
        assert comparison_data["project_ids"][0] != comparison_data["project_ids"][2]
    response = client.post("/experiments/compare", json={
        "experiment_ids": [experiment["id"] for experiment in selected],
    })
    assert response.status_code == 200


def test_response_fields_and_input_order(client, comparison_data):
    experiments = comparison_data["experiments"]
    order = [2, 0, 1, 3]
    ids = [experiments[index]["id"] for index in order]
    response = client.post("/experiments/compare", json={"experiment_ids": ids})
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"experiments", "best_by_metric"}
    assert [experiment["id"] for experiment in body["experiments"]] == ids
    assert set(body["best_by_metric"]) == set(METRICS)
    for item, index in zip(body["experiments"], order):
        original = experiments[index]
        assert set(item) == {"id", "experiment_no", "model_name", "batch_id", "project_id", "result"}
        for key in ("id", "experiment_no", "model_name", "batch_id"):
            assert item[key] == original[key]
        assert item["project_id"] == comparison_data["project_ids"][index]
        if index == 3:
            assert item["result"] is None
        else:
            assert set(item["result"]) == set(METRICS)
    for best in body["best_by_metric"].values():
        assert set(best) == {"direction", "value", "experiment_ids"}


def test_missing_result_and_partial_metrics_remain_null(client, comparison_data):
    partial, empty = comparison_data["experiments"][2:]
    response = client.post("/experiments/compare", json={"experiment_ids": [empty["id"], partial["id"]]})
    assert response.status_code == 200
    body = response.json()
    assert body["experiments"][0]["result"] is None
    assert body["experiments"][1]["result"] == {
        "accuracy": 0.75, "precision": None, "recall": 0.9, "f1": None, "loss": None,
    }
    assert body["best_by_metric"]["accuracy"]["experiment_ids"] == [partial["id"]]
    for metric in ("precision", "f1", "loss"):
        assert body["best_by_metric"][metric] == {
            "direction": "min" if metric == "loss" else "max", "value": None, "experiment_ids": [],
        }


@pytest.mark.parametrize("metric,value,indices,direction", [
    ("accuracy", 0.8, [1], "max"), ("precision", 0.8, [0, 1], "max"),
    ("recall", 0.9, [2], "max"), ("f1", 0.9, [1], "max"), ("loss", 0.2, [1], "min"),
])
def test_best_value_for_each_metric(client, comparison_data, metric, value, indices, direction):
    experiments = comparison_data["experiments"]
    response = client.post("/experiments/compare", json={
        "experiment_ids": [experiment["id"] for experiment in experiments],
    })
    assert response.status_code == 200
    assert response.json()["best_by_metric"][metric] == {
        "direction": direction, "value": value,
        "experiment_ids": [experiments[index]["id"] for index in indices],
    }


@pytest.mark.parametrize("metric", METRICS)
def test_tied_best_experiments_follow_input_order(client, comparison_data, metric):
    experiments = comparison_data["experiments"]
    best, worse = (0.3, 0.4) if metric == "loss" else (0.9, 0.8)
    for experiment, value in zip(experiments, [best, best, worse]):
        response = client.put(f"/experiments/{experiment['id']}/result", json={metric: value})
        assert response.status_code == 200
    ids = [experiments[index]["id"] for index in [1, 2, 0, 3]]
    response = client.post("/experiments/compare", json={"experiment_ids": ids})
    assert response.status_code == 200
    assert response.json()["best_by_metric"][metric] == {
        "direction": "min" if metric == "loss" else "max", "value": best,
        "experiment_ids": [ids[0], ids[2]],
    }


def test_all_experiments_without_results(client, sample_experiment, sample_batch, experiment_payload):
    second = client.post(f"/batches/{sample_batch['id']}/experiments", json={
        **experiment_payload, "experiment_no": "EXP-002",
    })
    assert second.status_code == 201
    ids = [second.json()["id"], sample_experiment["id"]]
    response = client.post("/experiments/compare", json={"experiment_ids": ids})
    assert response.status_code == 200
    body = response.json()
    assert [experiment["id"] for experiment in body["experiments"]] == ids
    assert all(experiment["result"] is None for experiment in body["experiments"])
    assert set(body["best_by_metric"]) == set(METRICS)
    for metric in METRICS:
        assert body["best_by_metric"][metric] == {
            "direction": "min" if metric == "loss" else "max", "value": None, "experiment_ids": [],
        }


@pytest.mark.parametrize("metric", METRICS)
def test_zero_is_a_valid_best_value(client, comparison_data, metric):
    first, second = comparison_data["experiments"][:2]
    for experiment, result in [(first, {metric: 0}), (second, {"loss": 0.5})]:
        response = client.put(f"/experiments/{experiment['id']}/result", json=result)
        assert response.status_code == 200
    response = client.post("/experiments/compare", json={"experiment_ids": [second["id"], first["id"]]})
    assert response.status_code == 200
    assert response.json()["best_by_metric"][metric] == {
        "direction": "min" if metric == "loss" else "max", "value": 0,
        "experiment_ids": [first["id"]],
    }


def test_result_update_is_visible_on_next_comparison(client, comparison_data):
    first, second = comparison_data["experiments"][:2]
    payload = {"experiment_ids": [first["id"], second["id"]]}
    before = client.post("/experiments/compare", json=payload)
    assert before.status_code == 200
    assert before.json()["best_by_metric"]["accuracy"]["experiment_ids"] == [second["id"]]
    update = client.put(f"/experiments/{first['id']}/result", json={"accuracy": 0.9})
    assert update.status_code == 200
    after = client.post("/experiments/compare", json=payload)
    assert after.status_code == 200
    assert after.json()["best_by_metric"]["accuracy"] == {
        "direction": "max", "value": 0.9, "experiment_ids": [first["id"]],
    }
    assert after.json()["experiments"][0]["result"] == {
        "accuracy": 0.9, "precision": None, "recall": None, "f1": None, "loss": None,
    }


def test_float_comparison_does_not_round_or_use_epsilon(client, comparison_data):
    first, second = comparison_data["experiments"][:2]
    for experiment, value in [(first, 0.3), (second, 0.30000000000000004)]:
        response = client.put(f"/experiments/{experiment['id']}/result", json={"accuracy": value})
        assert response.status_code == 200
    response = client.post("/experiments/compare", json={"experiment_ids": [first["id"], second["id"]]})
    assert response.status_code == 200
    assert response.json()["best_by_metric"]["accuracy"] == {
        "direction": "max", "value": 0.30000000000000004, "experiment_ids": [second["id"]],
    }


def test_comparison_is_one_read_query_without_commits_or_database_changes(
    client, comparison_data, test_engine, session_factory, monkeypatch,
):
    def snapshot():
        with test_engine.connect() as connection:
            return {table: connection.exec_driver_sql(f"SELECT * FROM {table} ORDER BY id").all()
                    for table in ("projects", "experiment_batches", "experiments", "experiment_results")}

    def forbid_commit(*args, **kwargs):
        raise AssertionError("Comparison must not commit")

    statements = []

    def record_statement(connection, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    before = snapshot()
    monkeypatch.setattr(session_factory.class_, "commit", forbid_commit)
    event.listen(test_engine, "before_cursor_execute", record_statement)
    try:
        response = client.post("/experiments/compare", json={
            "experiment_ids": [experiment["id"] for experiment in comparison_data["experiments"]],
        })
    finally:
        event.remove(test_engine, "before_cursor_execute", record_statement)
    assert response.status_code == 200
    assert len(statements) == 1
    assert statements[0].lstrip().upper().startswith("SELECT ")
    assert snapshot() == before


def test_swagger_has_explicit_comparison_response(client):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    spec = response.json()
    operation = spec["paths"]["/experiments/compare"]["post"]
    assert operation["tags"] == ["Experiment Comparison"]
    assert operation["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ExperimentCompareResponse",
    }
    schemas = spec["components"]["schemas"]
    assert set(schemas["ComparisonBestByMetric"]["properties"]) == set(METRICS)
    assert set(schemas["ComparisonBestByMetric"]["required"]) == set(METRICS)
    assert schemas["ExperimentCompareRequest"]["additionalProperties"] is False
