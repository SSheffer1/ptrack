"""App entry point. Run with: uv run fastapi dev src/ptrack/main.py

Everything the API does lives under /api. If the web app has been built
(`npm run build` in app/), its files are served from / as well, so one server
handles both the pages and the data.
"""

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .api import router
from .db import init_db

# Default: ptrack/app/dist next to the server/ directory.
STATIC_DIR = Path(os.environ.get("PTRACK_STATIC", Path(__file__).parents[3] / "app" / "dist"))


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


app = FastAPI(title="ptrack", lifespan=lifespan)
app.include_router(router, prefix="/api")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


if STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="web")
