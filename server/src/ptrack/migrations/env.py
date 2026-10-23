"""Alembic migration environment. See server/README.md for the commands."""

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

from ptrack import models  # noqa: F401  (registers the tables on SQLModel.metadata)
from ptrack.db import DATABASE_URL

config = context.config
# The server passes its URL in; from the command line, PTRACK_DB (or the default) applies.
if not config.get_main_option("sqlalchemy.url"):
    config.set_main_option("sqlalchemy.url", DATABASE_URL)

with engine_from_config(
    config.get_section(config.config_ini_section, {}), prefix="sqlalchemy.", poolclass=pool.NullPool
).connect() as connection:
    context.configure(
        connection=connection,
        target_metadata=SQLModel.metadata,
        # SQLite can't ALTER most things in place; batch mode copies the table instead.
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()
