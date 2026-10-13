"""Compute absolute deltas using the already loaded, current comparison data."""

from math import isfinite

from app.schemas import (
    BaselineComparison, BaselineMetricComparison, ComparisonExperiment,
    CustomMetricComparison, MetricDelta,
)


def metric_delta(baseline: ComparisonExperiment, experiment: ComparisonExperiment,
                 baseline_value: float | None, value: float | None,
                 direction: str, project_id: int | None) -> MetricDelta:
    reason = None
    if project_id is not None and baseline.project_id != project_id:
        reason = "baseline_project_mismatch"
    elif project_id is not None and experiment.project_id != project_id:
        reason = "experiment_project_mismatch"
    elif baseline.result is None:
        reason = "baseline_result_missing"
    elif experiment.result is None:
        reason = "experiment_result_missing"
    elif baseline_value is None:
        reason = "baseline_metric_missing"
    elif value is None:
        reason = "experiment_metric_missing"
    if reason:
        return MetricDelta(delta=None, status="unavailable", reason=reason)
    delta = value - baseline_value
    if not isfinite(delta):
        return MetricDelta(delta=None, status="unavailable", reason="overflow")
    status = "unchanged" if delta == 0 else (
        "improved" if (delta > 0) == (direction == "max") else "regressed"
    )
    return MetricDelta(delta=delta, status=status)


def build_baseline_comparison(experiments: list[ComparisonExperiment],
                              custom_metrics: list[CustomMetricComparison],
                              baseline_id: int) -> BaselineComparison:
    baseline = next(item for item in experiments if item.id == baseline_id)
    metrics = []
    for key, name in [("accuracy", "Accuracy"), ("precision", "Precision"),
                      ("recall", "Recall"), ("f1", "F1"), ("loss", "Loss")]:
        direction = "min" if key == "loss" else "max"
        baseline_value = getattr(baseline.result, key) if baseline.result else None
        metrics.append(BaselineMetricComparison(
            key=key, project_id=None, name=name, unit="" if key == "loss" else "比例",
            direction=direction, baseline_value=baseline_value,
            comparisons={item.id: metric_delta(baseline, item, baseline_value,
                         getattr(item.result, key) if item.result else None, direction, None)
                         for item in experiments},
        ))
    for custom in custom_metrics:
        definition = custom.definition
        baseline_value = custom.values[baseline_id]
        metrics.append(BaselineMetricComparison(
            key=definition.key, project_id=definition.project_id, name=definition.name,
            unit=definition.unit, direction=definition.direction, baseline_value=baseline_value,
            comparisons={item.id: metric_delta(baseline, item, baseline_value, custom.values[item.id],
                         definition.direction, definition.project_id) for item in experiments},
        ))
    return BaselineComparison(baseline_experiment_id=baseline_id, metrics=metrics)
