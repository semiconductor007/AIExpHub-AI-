"""No paid requests: snapshots use temporary DBs, provider I/O uses MockTransport."""

import asyncio
from dataclasses import replace
import json
from uuid import uuid4

import httpx
import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app import ai_provider
from app.ai_schemas import SECTIONS, SummarySelection
from app.ai_settings import AISettings, get_ai_settings, read_settings
from app.ai_snapshot import build_snapshot
from app.models import Experiment, ExperimentResult
from app.routers import ai_summaries


@pytest.fixture(autouse=True)
def ai_isolation(client, monkeypatch):
    settings = AISettings(enabled=True, api_key="test-only-secret", model="test-model")
    client.app.dependency_overrides[get_ai_settings] = lambda: settings
    ai_summaries._recent.clear()

    async def forbidden(*args, **kwargs):
        raise AssertionError("Tests must never call a real model")

    monkeypatch.setattr(ai_summaries, "call_deepseek", forbidden)
    yield settings
    ai_summaries._recent.clear()


@pytest.fixture
def records(client, sample_batch):
    result = []
    for index, accuracy in enumerate((0, 0.8, None)):
        item = client.post(f"/batches/{sample_batch['id']}/experiments", json={
            "experiment_no": f"AI-{index}", "model_name": "model", "notes": "PRIVATE NOTE",
            "parameters": {"a.b": 1, "a": {"b": 2}, "x/y": [None, 0], "private": "PRIVATE PARAM",
                           **({"only_one": None} if index == 0 else {})},
        }).json()
        if accuracy is not None:
            assert client.post(f"/experiments/{item['id']}/result", json={"accuracy": accuracy, "loss": 0}).status_code == 201
        result.append(item)
    return result


def choices(records, **extra):
    return {"experiment_ids": [item["id"] for item in records], **extra}


def preview(client, records, **extra):
    response = client.post("/ai/summaries/preview", json=choices(records, **extra))
    assert response.status_code == 200, response.text
    return response.json()


def narrative(snapshot):
    item_id = snapshot["data"]["experiment_ids"][0]
    return {"sections": [{"key": key, "items": [{
        "kind": "suggestion" if key == "next_steps" else "observation", "text": "请核对评测条件。",
        "experiment_ids": [item_id], "metric_ids": [], "evidence_ids": [f"experiment:{item_id}"],
    }]} for key in SECTIONS]}


def generator_payload(records, snapshot, **extra):
    return {**choices(records), "fingerprint": snapshot["fingerprint"], "request_id": str(uuid4()), **extra}


def test_status_does_not_leak_key_or_call_provider(client):
    response = client.get("/ai/summaries/status")
    assert response.json()["ready"] is True
    assert "test-only-secret" not in response.text


def test_snapshot_is_readonly_and_excludes_unselected_content(client, records, db_session):
    snapshot = preview(client, records, baseline_experiment_id=records[0]["id"])
    accuracy = next(fact for fact in snapshot["facts"] if fact["key"] == "accuracy")
    assert accuracy["values"] == {str(records[0]["id"]): 0, str(records[1]["id"]): 0.8, str(records[2]["id"]): None}
    assert accuracy["best"]["experiment_ids"] == [records[1]["id"]]
    loss = next(fact for fact in snapshot["facts"] if fact["key"] == "loss")
    assert loss["best"]["experiment_ids"] == [records[0]["id"], records[1]["id"]]
    payload = json.dumps(snapshot["messages"])
    assert "PRIVATE" not in payload and "notes" not in payload and "test-only-secret" not in payload
    assert len(list(db_session.scalars(select(Experiment)))) == 3
    assert len(list(db_session.scalars(select(ExperimentResult)))) == 2


def test_json_pointer_selection_and_null_versus_missing(client, records):
    snapshot = preview(client, records, parameter_paths=["/a.b", "/a/b", "/x~1y/0", "/only_one"])
    assert "/x~1y/1" in snapshot["parameter_paths"]
    experiments = snapshot["data"]["evidence"][:3]
    params = experiments[0]["data"]["parameters"]
    assert params["/a.b"]["value"] == 1 and params["/a/b"]["value"] == 2
    assert params["/x~1y/0"] == {"present": True, "value": None}
    assert params["/only_one"] == {"present": True, "value": None}
    assert experiments[1]["data"]["parameters"]["/only_one"] == {"present": False, "value": None}


@pytest.mark.parametrize("extra", [
    {"parameter_paths": ["/missing"]}, {"primary_metric": "system:f1"}, {"primary_metric": "unknown"},
    {"baseline_experiment_id": 999999}, {"experiment_ids": [1, 1]}, {"experiment_ids": [True, 2]},
    {"experiment_ids": [1]}, {"experiment_ids": list(range(1, 12))}, {"parameter_paths": ["/a", "/a"]},
])
def test_invalid_choices(client, records, extra):
    assert client.post("/ai/summaries/preview", json=choices(records, **extra)).status_code == 422


def test_missing_resource_and_cross_project(client, records):
    assert client.post("/ai/summaries/preview", json=choices(records, experiment_ids=[records[0]["id"], 9999])).status_code == 404
    project = client.post("/projects", json={"name": "Other"}).json()
    batch = client.post(f"/projects/{project['id']}/batches", json={"name": "Other"}).json()
    item = client.post(f"/batches/{batch['id']}/experiments", json={"experiment_no": "OTHER", "model_name": "m", "parameters": {"x": 1}}).json()
    assert client.post("/ai/summaries/preview", json=choices(records, experiment_ids=[records[0]["id"], item["id"]])).status_code == 422


def test_no_common_valid_metric_is_rejected(client, records):
    assert client.put(f"/experiments/{records[1]['id']}/result", json={"f1": 0.7}).status_code == 200
    assert client.post("/ai/summaries/preview", json=choices(records)).status_code == 422


def test_custom_metric_direction_and_scope(client, records, sample_project):
    metric = client.post(f"/projects/{sample_project['id']}/metrics", json={"key": "latency", "name": "延迟", "unit": "ms", "direction": "min"}).json()
    for record, value in zip(records[:2], [10, 0]):
        assert client.put(f"/experiments/{record['id']}/result", json={"custom_metrics": {"latency": value}}).status_code == 200
    metric_id = f"custom:{sample_project['id']}:{metric['id']}:latency"
    snapshot = preview(client, records, primary_metric=metric_id)
    fact = next(fact for fact in snapshot["facts"] if fact["id"] == metric_id)
    assert fact["unit"] == "ms" and fact["direction"] == "min"
    assert fact["best"]["experiment_ids"] == [records[1]["id"]]


def test_size_limit_rejects_without_truncation(client, records, ai_isolation):
    client.app.dependency_overrides[get_ai_settings] = lambda: replace(ai_isolation, max_input_bytes=64)
    assert client.post("/ai/summaries/preview", json=choices(records)).status_code == 422


def test_preview_change_blocks_paid_call_and_freshness_check(client, records):
    snapshot = preview(client, records)
    check = {**choices(records), "fingerprint": snapshot["fingerprint"]}
    assert client.post("/ai/summaries/check", json=check).json()["current"] is True
    # Unselected parameter changes must still invalidate the summary snapshot.
    assert client.put(f"/experiments/{records[0]['id']}", json={
        **{key: records[0][key] for key in ("experiment_no", "model_name")}, "parameters": {"new": 1},
    }).status_code == 200
    assert client.post("/ai/summaries/check", json=check).json()["current"] is False
    assert client.post("/ai/summaries/generate", json=generator_payload(records, snapshot)).status_code == 409


def test_generate_releases_transaction_and_prevents_duplicate(client, records, monkeypatch):
    snapshot = preview(client, records)
    calls = []

    async def fake(current, settings):
        calls.append(current)
        # A separate connection can write while the provider is running.
        assert client.put(f"/experiments/{records[0]['id']}/result", json={"accuracy": 0.1}).status_code == 200
        return {"model": "resolved-test-model", "narrative": narrative(current)}

    monkeypatch.setattr(ai_summaries, "call_deepseek", fake)
    payload = generator_payload(records, snapshot)
    response = client.post("/ai/summaries/generate", json=payload)
    assert response.status_code == 200, response.text
    assert response.json()["stale"] is True and response.json()["model"] == "resolved-test-model"
    assert client.post("/ai/summaries/generate", json=payload).status_code == 409
    assert len(calls) == 1


def test_failed_request_id_cannot_be_automatically_retried(client, records, monkeypatch):
    snapshot = preview(client, records)
    calls = []

    async def fake(*args):
        calls.append(1)
        raise HTTPException(504, "timeout")

    monkeypatch.setattr(ai_summaries, "call_deepseek", fake)
    payload = generator_payload(records, snapshot)
    assert client.post("/ai/summaries/generate", json=payload).status_code == 504
    assert client.post("/ai/summaries/generate", json=payload).status_code == 409
    assert len(calls) == 1


def test_concurrent_generation_rejected(client, records):
    snapshot = preview(client, records)
    ai_summaries._gate.acquire()
    try:
        assert client.post("/ai/summaries/generate", json=generator_payload(records, snapshot)).status_code == 409
    finally:
        ai_summaries._gate.release()


@pytest.mark.parametrize("settings", [AISettings(), AISettings(enabled=True), AISettings(error="Bad configuration")])
def test_unconfigured_ai_does_not_break_core(client, records, settings):
    client.app.dependency_overrides[get_ai_settings] = lambda: settings
    assert client.get("/ai/summaries/status").json()["ready"] is False
    assert client.post("/ai/summaries/generate", json={**choices(records), "fingerprint": "0" * 64, "request_id": str(uuid4())}).status_code == 503
    assert client.post("/experiments/compare", json=choices(records)).status_code == 200


def test_config_file_quotes_environment_priority_and_no_expansion(tmp_path, monkeypatch):
    config = tmp_path / ".env"
    for key in ("AI_SUMMARY_ENABLED", "DEEPSEEK_API_KEY", "DEEPSEEK_MODEL", "DEEPSEEK_BASE_URL",
                "AI_SUMMARY_TIMEOUT_SECONDS", "AI_SUMMARY_MAX_INPUT_BYTES", "AI_SUMMARY_MAX_EXPERIMENTS", "AI_SUMMARY_MAX_OUTPUT_TOKENS"):
        monkeypatch.delenv(key, raising=False)
    config.write_text('AI_SUMMARY_ENABLED=true\nDEEPSEEK_API_KEY="local-key"\nDEEPSEEK_MODEL=model-a\n', encoding="utf-8-sig")
    assert read_settings(config).api_key == "local-key"
    monkeypatch.setenv("DEEPSEEK_API_KEY", "env-key")
    monkeypatch.setenv("DEEPSEEK_MODEL", "${DEEPSEEK_API_KEY}")
    settings = read_settings(config)
    assert settings.api_key == "env-key" and settings.model == "${DEEPSEEK_API_KEY}"
    assert "env-key" not in repr(settings)
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://example.com")
    assert read_settings(config).error


@pytest.mark.parametrize("mutate", [
    lambda output: output["sections"][0]["items"][0].update(evidence_ids=["unknown"]),
    lambda output: output["sections"][0]["items"][0].update(experiment_ids=[999]),
    lambda output: output["sections"][0]["items"][0].update(metric_ids=["unknown"]),
    lambda output: output["sections"][0]["items"][0].update(metric_ids=["system:accuracy"]),
    lambda output: output["sections"][0]["items"][0].update(text=""),
    lambda output: output["sections"][1].update(key="overview"),
    lambda output: output.update(extra="not allowed"),
])
def test_narrative_schema_and_evidence_rejection(client, records, mutate):
    snapshot = preview(client, records)
    output = narrative(snapshot)
    mutate(output)
    with pytest.raises(HTTPException) as exc:
        ai_provider.validate_narrative(json.dumps(output), snapshot)
    assert exc.value.status_code == 502


def install_mock_transport(monkeypatch, handler):
    original = httpx.AsyncClient
    def factory(**kwargs):
        return original(transport=httpx.MockTransport(handler), **kwargs)
    monkeypatch.setattr(ai_provider.httpx, "AsyncClient", factory)


def test_provider_sends_only_confirmed_data_and_validates_response(client, records, monkeypatch, ai_isolation):
    snapshot = preview(client, records)
    requests = []

    def handler(request):
        requests.append(request)
        payload = json.loads(request.content)
        assert request.url == "https://api.deepseek.com/chat/completions"
        assert payload["stream"] is False and payload["response_format"] == {"type": "json_object"}
        assert b"PRIVATE PARAM" not in request.content
        return httpx.Response(200, json={"model": "resolved", "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(narrative(snapshot))}}]})

    install_mock_transport(monkeypatch, handler)
    result = asyncio.run(ai_provider.call_deepseek(snapshot, ai_isolation))
    assert result["model"] == "resolved" and len(requests) == 1


@pytest.mark.parametrize("code,expected", [(401, 502), (402, 502), (403, 502), (429, 502), (500, 502), (302, 502)])
def test_provider_errors_sanitized_no_retry(client, records, monkeypatch, ai_isolation, code, expected):
    snapshot = preview(client, records)
    requests = []
    def handler(request):
        requests.append(request)
        return httpx.Response(code, text="test-only-secret PRIVATE PROVIDER BODY", headers={"location": "https://example.com"})
    install_mock_transport(monkeypatch, handler)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(ai_provider.call_deepseek(snapshot, ai_isolation))
    assert exc.value.status_code == expected and "secret" not in exc.value.detail
    assert len(requests) == 1


@pytest.mark.parametrize("body", [
    {}, {"model": "m", "choices": []},
    {"model": "m", "choices": [{"finish_reason": "length", "message": {"content": "{}"}}]},
    {"model": "m", "choices": [{"finish_reason": "stop", "message": {"content": ""}}]},
    {"model": "m", "choices": [{"finish_reason": "stop", "message": {"content": "invalid json"}}]},
    {"model": "m", "choices": [{"finish_reason": "stop", "message": {"content": "{}", "tool_calls": [{}]}}]},
])
def test_provider_empty_malformed_truncated(client, records, monkeypatch, ai_isolation, body):
    snapshot = preview(client, records)
    install_mock_transport(monkeypatch, lambda request: httpx.Response(200, json=body))
    with pytest.raises(HTTPException) as exc:
        asyncio.run(ai_provider.call_deepseek(snapshot, ai_isolation))
    assert exc.value.status_code == 502


def test_total_timeout_not_just_per_read_timeout(client, records, monkeypatch, ai_isolation):
    snapshot = preview(client, records)
    async def slow(request):
        await asyncio.sleep(0.05)
        return httpx.Response(200, json={})
    install_mock_transport(monkeypatch, slow)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(ai_provider.call_deepseek(snapshot, replace(ai_isolation, timeout=0.01)))
    assert exc.value.status_code == 504


def test_provider_connection_failure(client, records, monkeypatch, ai_isolation):
    snapshot = preview(client, records)
    def failed(request):
        raise httpx.ConnectError("PRIVATE network info", request=request)
    install_mock_transport(monkeypatch, failed)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(ai_provider.call_deepseek(snapshot, ai_isolation))
    assert exc.value.status_code == 502 and "PRIVATE" not in exc.value.detail
