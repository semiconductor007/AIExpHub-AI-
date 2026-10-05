"""SQLite connection infrastructure; no business models or tables yet."""

from pathlib import Path

from sqlalchemy import URL, create_engine
from sqlalchemy.orm import sessionmaker


BACKEND_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = BACKEND_DIR / "data" / "aiexphub.db"
DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    URL.create("sqlite+pysqlite", database=str(DATABASE_PATH)),
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(bind=engine)
