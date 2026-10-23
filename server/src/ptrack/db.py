"""Database connection. Set PTRACK_DB to change where the SQLite file lives."""

import os
from collections.abc import Iterator

from sqlmodel import Session, SQLModel, create_engine

DATABASE_URL = os.environ.get("PTRACK_DB", "sqlite:///ptrack.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


def init_db() -> None:
    # Creates missing tables only. Schema changes to existing tables will need
    # real migrations (Alembic) once there is data worth keeping.
    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
