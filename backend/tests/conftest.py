"""Function-scoped SQLite databases and HTTP fixtures; production is never used."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import URL, create_engine, event
from sqlalchemy.orm import sessionmaker

from app import database, main
from app.database import Base, enable_sqlite_foreign_keys, get_db


@pytest.fixture(autouse=True)
def forbid_production_database(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Tests must not connect to or initialize the production database")

    monkeypatch.setattr(database.engine, "connect", forbidden)
    monkeypatch.setattr(database.engine, "raw_connection", forbidden)
    monkeypatch.setattr(main, "SessionLocal", forbidden)
    monkeypatch.setattr(main, "init_db", forbidden)


@pytest.fixture
def test_engine(tmp_path, forbid_production_database):
    engine = create_engine(
        URL.create("sqlite+pysqlite", database=str(tmp_path / "test.db")),
        connect_args={"check_same_thread": False},
    )
    event.listen(engine, "connect", enable_sqlite_foreign_keys)
    try:
        Base.metadata.create_all(bind=engine)
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def session_factory(test_engine):
    return sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)


@pytest.fixture
def db_session(session_factory):
    with session_factory() as session:
        try:
            yield session
        finally:
            session.rollback()


@pytest.fixture
def client(session_factory, monkeypatch):
    def override_get_db():
        with session_factory() as session:
            try:
                yield session
            except Exception:
                session.rollback()
                raise

    main.app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr(main, "SessionLocal", session_factory)
    # Without a context manager TestClient does not run the production lifespan.
    http_client = None
    try:
        http_client = TestClient(main.app)
        yield http_client
    finally:
        if http_client is not None:
            http_client.close()
        main.app.dependency_overrides.clear()


@pytest.fixture
def sample_project(client):
    response = client.post("/projects", json={"name": "Sample project", "description": "study"})
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def sample_batch(client, sample_project):
    response = client.post(
        f"/projects/{sample_project['id']}/batches", json={"name": "Sample batch"}
    )
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def experiment_payload():
    return {
        "experiment_no": "EXP-001",
        "model_name": "Janus-Pro-1B",
        "parameters": {"temperature": 0.7},
        "notes": "baseline",
    }


@pytest.fixture
def sample_experiment(client, sample_batch, experiment_payload):
    response = client.post(
        f"/batches/{sample_batch['id']}/experiments", json=experiment_payload
    )
    assert response.status_code == 201
    return response.json()
