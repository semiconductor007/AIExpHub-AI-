import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.models import Experiment, ExperimentBatch, ExperimentResult, Project


def test_foreign_keys_enabled_on_each_connection(test_engine):
    with test_engine.connect() as first, test_engine.connect() as second:
        assert first.scalar(text("PRAGMA foreign_keys")) == 1
        assert second.scalar(text("PRAGMA foreign_keys")) == 1


def test_experiment_number_database_unique(db_session, sample_experiment):
    db_session.add(Experiment(
        batch_id=sample_experiment["batch_id"],
        experiment_no=sample_experiment["experiment_no"],
        model_name="direct probe", parameters={"probe": True},
    ))
    with pytest.raises(IntegrityError, match="UNIQUE constraint failed: experiments.experiment_no"):
        db_session.commit()
    db_session.rollback()
    assert db_session.scalar(text("SELECT 1")) == 1
    assert list(db_session.scalars(select(Experiment.id))) == [sample_experiment["id"]]


def test_result_experiment_database_unique(db_session, sample_experiment):
    original = ExperimentResult(experiment_id=sample_experiment["id"], accuracy=0.8)
    db_session.add(original)
    db_session.commit()
    original_id = original.id
    db_session.add(ExperimentResult(experiment_id=sample_experiment["id"], loss=0.5))
    with pytest.raises(IntegrityError, match="UNIQUE constraint failed: experiment_results.experiment_id"):
        db_session.commit()
    db_session.rollback()
    assert db_session.scalar(text("SELECT 1")) == 1
    assert list(db_session.scalars(select(ExperimentResult.id))) == [original_id]
    assert db_session.get(ExperimentResult, original_id).accuracy == 0.8


@pytest.mark.parametrize(
    ("metrics", "constraint"),
    [
        ({"accuracy": 1.1}, "ck_experiment_results_accuracy_range"),
        ({"loss": -0.1}, "ck_experiment_results_loss_range"),
        ({}, "ck_experiment_results_at_least_one_metric"),
    ],
)
def test_result_database_checks(db_session, sample_experiment, metrics, constraint):
    db_session.add(ExperimentResult(experiment_id=sample_experiment["id"], **metrics))
    with pytest.raises(IntegrityError, match=constraint):
        db_session.commit()
    db_session.rollback()
    assert db_session.scalar(text("SELECT 1")) == 1
    assert db_session.scalar(select(ExperimentResult.id)) is None
    valid = ExperimentResult(experiment_id=sample_experiment["id"], loss=0)
    db_session.add(valid)
    db_session.commit()
    assert db_session.get(ExperimentResult, valid.id).loss == 0


def test_project_database_restrict(db_session, sample_batch):
    project = db_session.get(Project, sample_batch["project_id"])
    assert [batch.id for batch in project.batches] == [sample_batch["id"]]
    db_session.delete(project)
    with pytest.raises(IntegrityError, match="FOREIGN KEY constraint failed"):
        db_session.commit()
    db_session.rollback()
    assert db_session.scalar(text("SELECT 1")) == 1
    assert db_session.get(Project, sample_batch["project_id"]) is not None
    assert db_session.get(ExperimentBatch, sample_batch["id"]) is not None


def test_batch_database_restrict(db_session, sample_experiment):
    batch = db_session.get(ExperimentBatch, sample_experiment["batch_id"])
    assert [experiment.id for experiment in batch.experiments] == [sample_experiment["id"]]
    db_session.delete(batch)
    with pytest.raises(IntegrityError, match="FOREIGN KEY constraint failed"):
        db_session.commit()
    db_session.rollback()
    assert db_session.scalar(text("SELECT 1")) == 1
    assert db_session.get(ExperimentBatch, sample_experiment["batch_id"]) is not None
    assert db_session.get(Experiment, sample_experiment["id"]) is not None


def test_experiment_database_cascade_with_loaded_result(db_session, sample_experiment):
    experiment = db_session.get(Experiment, sample_experiment["id"])
    result = ExperimentResult(experiment=experiment, loss=0)
    db_session.add(result)
    db_session.commit()
    result_id = result.id
    assert experiment.result is result
    db_session.delete(experiment)
    db_session.commit()
    assert db_session.scalar(select(Experiment.id).where(Experiment.id == sample_experiment["id"])) is None
    assert db_session.scalar(select(ExperimentResult.id).where(ExperimentResult.id == result_id)) is None
    assert db_session.execute(text("PRAGMA foreign_key_check")).all() == []
