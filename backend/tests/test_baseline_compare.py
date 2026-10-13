"""Baseline deltas preserve legacy comparison, nulls, scope and read-only access."""

import pytest
from sqlalchemy import event


@pytest.fixture
def baseline_data(client, sample_experiment, sample_batch, experiment_payload):
    other_batch = client.post(f"/projects/{sample_batch['project_id']}/batches", json={"name": "Different batch"}).json()
    candidate = client.post(f"/batches/{other_batch['id']}/experiments", json={**experiment_payload, "experiment_no": "CANDIDATE"}).json()
    empty = client.post(f"/batches/{sample_batch['id']}/experiments", json={**experiment_payload, "experiment_no": "EMPTY"}).json()
    for experiment, values in [(sample_experiment, {"accuracy": 0.8, "precision": 0, "recall": 0.6, "loss": 0.4}),
                               (candidate, {"accuracy": 0.83, "precision": 0, "f1": 0.9, "loss": 0.3})]:
        assert client.post(f"/experiments/{experiment['id']}/result", json=values).status_code == 201
    return sample_experiment, candidate, empty


def compare(client, experiments, baseline=None):
    return client.post('/experiments/compare', json={
        'experiment_ids': [item['id'] for item in experiments], 'baseline_experiment_id': baseline,
    })


def delta(body, key, experiment_id, project=None):
    metric = next(item for item in body['baseline_comparison']['metrics'] if item['key'] == key and item['project_id'] == project)
    return metric['comparisons'][str(experiment_id)]


@pytest.mark.parametrize('value', [0, -1, True, '1', 1.0, [], {}])
def test_invalid_baseline_id(client, sample_experiment, value):
    response = client.post('/experiments/compare', json={'experiment_ids': [sample_experiment['id'], 99999], 'baseline_experiment_id': value})
    assert response.status_code == 422


def test_baseline_must_be_selected_and_exist(client, baseline_data):
    baseline, candidate, empty = baseline_data
    response = compare(client, [baseline, candidate], empty['id'])
    assert response.status_code == 422 and '基准' in response.text
    response = compare(client, [baseline, {'id': 99999}], 99999)
    assert response.status_code == 404 and response.json()['detail'] == 'Experiment not found: 99999'


def test_no_baseline_preserves_response_and_best_values(client, baseline_data):
    baseline, candidate, _ = baseline_data
    legacy = client.post('/experiments/compare', json={'experiment_ids': [candidate['id'], baseline['id']]}).json()
    explicit_null = compare(client, [candidate, baseline]).json()
    with_baseline = compare(client, [candidate, baseline], baseline['id']).json()
    assert explicit_null == legacy and 'baseline_comparison' not in legacy
    assert {key: value for key, value in with_baseline.items() if key != 'baseline_comparison'} == legacy
    assert [item['id'] for item in with_baseline['experiments']] == [candidate['id'], baseline['id']]
    assert with_baseline['baseline_comparison']['baseline_experiment_id'] == baseline['id']


def test_max_min_equal_zero_and_missing_metrics(client, baseline_data):
    baseline, candidate, _ = baseline_data
    response = compare(client, [baseline, candidate], baseline['id'])
    assert response.status_code == 200
    body = response.json()
    accuracy = delta(body, 'accuracy', candidate['id'])
    assert accuracy['delta'] == pytest.approx(0.03) and accuracy['status'] == 'improved' and accuracy['reason'] is None
    loss = delta(body, 'loss', candidate['id'])
    assert loss['delta'] == pytest.approx(-0.1) and loss['status'] == 'improved'
    assert delta(body, 'precision', candidate['id']) == {'delta': 0, 'status': 'unchanged', 'reason': None}
    assert delta(body, 'accuracy', baseline['id']) == {'delta': 0, 'status': 'unchanged', 'reason': None}
    assert delta(body, 'recall', candidate['id']) == {'delta': None, 'status': 'unavailable', 'reason': 'experiment_metric_missing'}
    assert delta(body, 'f1', candidate['id']) == {'delta': None, 'status': 'unavailable', 'reason': 'baseline_metric_missing'}
    reverse = compare(client, [baseline, candidate], candidate['id']).json()
    assert delta(reverse, 'accuracy', baseline['id'])['status'] == 'regressed'
    assert delta(reverse, 'loss', baseline['id'])['status'] == 'regressed'
    precision = next(m for m in body['baseline_comparison']['metrics'] if m['key'] == 'precision')
    assert precision['baseline_value'] == 0


def test_no_result_has_explicit_reason(client, baseline_data):
    baseline, candidate, empty = baseline_data
    body = compare(client, [baseline, candidate, empty], baseline['id']).json()
    assert all(m['comparisons'][str(empty['id'])]['reason'] == 'experiment_result_missing' for m in body['baseline_comparison']['metrics'])
    body = compare(client, [baseline, candidate, empty], empty['id']).json()
    assert all(value['delta'] is None and value['reason'] == 'baseline_result_missing'
               for metric in body['baseline_comparison']['metrics'] for value in metric['comparisons'].values())


def test_custom_metrics_scoped_to_project_and_units(client, sample_batch, experiment_payload, baseline_data):
    baseline, candidate, _ = baseline_data
    project = sample_batch['project_id']
    definition = {'key': 'latency_ms', 'name': '耗时', 'unit': 'ms', 'direction': 'min'}
    assert client.post(f'/projects/{project}/metrics', json=definition).status_code == 201
    other_project = client.post('/projects', json={'name': 'Other project'}).json()
    other_batch = client.post(f"/projects/{other_project['id']}/batches", json={'name': 'Other batch'}).json()
    other = client.post(f"/batches/{other_batch['id']}/experiments", json={**experiment_payload, 'experiment_no': 'OTHER'}).json()
    assert client.post(f"/projects/{other_project['id']}/metrics", json={**definition, 'unit': '分', 'direction': 'max'}).status_code == 201
    for item, value in [(baseline, 30), (candidate, 18)]:
        assert client.put(f"/experiments/{item['id']}/result", json={'accuracy': 0.8, 'custom_metrics': {'latency_ms': value}}).status_code == 200
    assert client.post(f"/experiments/{other['id']}/result", json={'accuracy': 0.9, 'custom_metrics': {'latency_ms': 80}}).status_code == 201
    body = compare(client, [candidate, other, baseline], baseline['id']).json()
    assert delta(body, 'latency_ms', candidate['id'], project) == {'delta': -12, 'status': 'improved', 'reason': None}
    assert delta(body, 'latency_ms', other['id'], project)['reason'] == 'experiment_project_mismatch'
    assert all(v['reason'] == 'baseline_project_mismatch' for m in body['baseline_comparison']['metrics']
               if m['project_id'] == other_project['id'] for v in m['comparisons'].values())
    custom = [m for m in body['baseline_comparison']['metrics'] if m['project_id'] is not None]
    assert [m['unit'] for m in custom] == ['ms', '分']
    assert delta(body, 'accuracy', other['id'])['delta'] == pytest.approx(0.1)  # Existing cross-project numeric rule.


def test_custom_negative_zero_tiny_and_overflow(client, sample_batch, baseline_data):
    baseline, candidate, _ = baseline_data
    for key, direction in [('negative', 'max'), ('tiny', 'max'), ('extreme', 'min')]:
        assert client.post(f"/projects/{sample_batch['project_id']}/metrics", json={'key': key, 'name': key, 'direction': direction}).status_code == 201
    for item, custom in [(baseline, {'negative': -10, 'tiny': 0, 'extreme': -1e308}),
                         (candidate, {'negative': 0, 'tiny': 5e-324, 'extreme': 1e308})]:
        assert client.put(f"/experiments/{item['id']}/result", json={'custom_metrics': custom}).status_code == 200
    body = compare(client, [baseline, candidate], baseline['id']).json()
    project = sample_batch['project_id']
    assert delta(body, 'negative', candidate['id'], project) == {'delta': 10, 'status': 'improved', 'reason': None}
    assert delta(body, 'tiny', candidate['id'], project)['delta'] == 5e-324
    assert delta(body, 'tiny', candidate['id'], project)['status'] == 'improved'
    assert delta(body, 'extreme', candidate['id'], project) == {'delta': None, 'status': 'unavailable', 'reason': 'overflow'}


def test_recomparison_reads_latest_baseline_and_candidate(client, baseline_data):
    baseline, candidate, _ = baseline_data
    original = compare(client, [baseline, candidate], baseline['id']).json()
    assert delta(original, 'accuracy', candidate['id'])['status'] == 'improved'
    assert client.put(f"/experiments/{baseline['id']}/result", json={'accuracy': 0.9}).status_code == 200
    latest = compare(client, [baseline, candidate], baseline['id']).json()
    assert delta(latest, 'accuracy', candidate['id'])['status'] == 'regressed'
    assert client.put(f"/experiments/{candidate['id']}/result", json={'accuracy': 1}).status_code == 200
    latest = compare(client, [baseline, candidate], baseline['id']).json()
    assert delta(latest, 'accuracy', candidate['id'])['delta'] == pytest.approx(0.1)
    assert latest['best_by_metric']['accuracy']['experiment_ids'] == [candidate['id']]


def test_baseline_comparison_single_select_no_commit(client, baseline_data, test_engine):
    baseline, candidate, _ = baseline_data
    statements, commits = [], []
    def capture(conn, cursor, statement, parameters, context, many): statements.append(statement)
    def commit(conn): commits.append(True)
    event.listen(test_engine, 'before_cursor_execute', capture)
    event.listen(test_engine, 'commit', commit)
    try:
        response = compare(client, [baseline, candidate], baseline['id'])
    finally:
        event.remove(test_engine, 'before_cursor_execute', capture)
        event.remove(test_engine, 'commit', commit)
    assert response.status_code == 200 and len(statements) == 1 and not commits
