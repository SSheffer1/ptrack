# ptrack server

FastAPI + SQLite. REST API for the web UI, `/sync` for the phone app.

```bash
uv run fastapi dev src/ptrack/main.py   # dev server with auto-reload on :8000
uv run pytest                           # tests
```

API docs (interactive): http://localhost:8000/docs. Database file: `ptrack.db` (override with `PTRACK_DB`).

## Changing the database schema

The server applies migrations (`src/ptrack/migrations/versions/`) on startup, so
existing data is converted, not lost. After editing `models.py`:

```bash
# 1. Stop the dev server first: its auto-reload would run a half-written migration.
# 2. Generate the migration against a scratch database at the current schema:
PTRACK_DB=sqlite:////tmp/scratch.db uv run alembic upgrade head
PTRACK_DB=sqlite:////tmp/scratch.db uv run alembic revision --autogenerate -m "what changed"
# 3. Read the generated file; add data conversion if existing rows need it.
# 4. uv run pytest   (test_migrations checks migrations match the models)
```

| File | What |
|---|---|
| `src/ptrack/models.py` | Database tables |
| `src/ptrack/sync.py` | Change log, last-write-wins, ticket numbering |
| `src/ptrack/api.py` | HTTP endpoints |
| `src/ptrack/recurrence.py` | Repeat rules for recurring tickets |
| `src/ptrack/db.py` | Database connection, runs migrations |
| `src/ptrack/migrations/` | Alembic schema migrations |
| `src/ptrack/main.py` | App entry point |
