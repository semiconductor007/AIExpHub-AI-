"""SQLite connection infrastructure and local table initialization."""

from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import URL, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


BACKEND_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = BACKEND_DIR / "data" / "aiexphub.db"
DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    URL.create("sqlite+pysqlite", database=str(DATABASE_PATH)),
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine, "connect")
def enable_sqlite_foreign_keys(dbapi_connection, connection_record):
    previous_autocommit = dbapi_connection.autocommit
    dbapi_connection.autocommit = True
    try:
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
        finally:
            cursor.close()
    finally:
        dbapi_connection.autocommit = previous_autocommit


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    with SessionLocal() as db:
        try:
            yield db
        except Exception:
            db.rollback()
            raise


def init_db() -> None:
    from app import models  # Register the business models before creating tables.
    from app.migrations import backup_before_mapping_templates, upgrade_project_metrics
    from app.metric_constraints import install_metric_constraints

    upgrade_project_metrics(engine)
    backup_before_mapping_templates(engine)
    Base.metadata.create_all(bind=engine)
    install_metric_constraints(engine)
