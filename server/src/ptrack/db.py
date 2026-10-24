"""Database connection and migrations. The database is set in ptrack.toml ([database] url) or PTRACK_DB."""

from collections.abc import Iterator
from pathlib import Path
from typing import Annotated

from alembic import command
from alembic.config import Config
from fastapi import Depends
from sqlmodel import Session, create_engine

from .config import settings

DATABASE_URL = settings.database_url

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


def alembic_config(url: str = DATABASE_URL) -> Config:
    config = Config()
    config.set_main_option("script_location", str(Path(__file__).parent / "migrations"))
    config.set_main_option("sqlalchemy.url", url)
    return config


def init_db() -> None:
    """Bring the database up to the latest schema (creates it on first run).

    Schema changes go through migrations in migrations/versions/, so existing
    data is converted rather than lost. See server/README.md.
    """
    command.upgrade(alembic_config(), "head")


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
