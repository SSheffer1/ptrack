"""The migrations must build exactly the schema the models describe.

If this fails after changing models.py, generate a migration (see server/README.md).
"""

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine
from sqlmodel import SQLModel

from ptrack.db import alembic_config


def test_migrations_match_models(tmp_path):
    url = f"sqlite:///{tmp_path / 'test.db'}"
    command.upgrade(alembic_config(url), "head")
    with create_engine(url).connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), SQLModel.metadata)
    assert diff == []


def test_migrations_downgrade_cleanly(tmp_path):
    url = f"sqlite:///{tmp_path / 'test.db'}"
    command.upgrade(alembic_config(url), "head")
    command.downgrade(alembic_config(url), "base")
