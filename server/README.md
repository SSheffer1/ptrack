# ptrack server

FastAPI + SQLite. REST API for the web UI, `/sync` for the phone app.

```bash
uv run fastapi dev src/ptrack/main.py   # dev server with auto-reload on :8000
uv run pytest                           # tests
```

API docs (interactive): http://localhost:8000/docs. Database file: `ptrack.db` (override with `PTRACK_DB`).

| File | What |
|---|---|
| `src/ptrack/models.py` | Database tables |
| `src/ptrack/sync.py` | Change log, last-write-wins, ticket numbering |
| `src/ptrack/api.py` | HTTP endpoints |
| `src/ptrack/db.py` | Database connection |
| `src/ptrack/main.py` | App entry point |
