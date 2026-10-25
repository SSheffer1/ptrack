"""App entry point. Run with: uv run fastapi dev src/ptrack/main.py

Everything the API does lives under /api. If the web app has been built
(`npm run build` in app/), its files are served from / as well, so one server
handles both the pages and the data.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.staticfiles import StaticFiles

from .api import router
from .auth import admin_router, public_router
from .auth import router as auth_router
from .auth import current_actor
from .config import settings
from .db import init_db

STATIC_DIR = Path(settings.static_dir)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


app = FastAPI(title="PTrack", lifespan=lifespan)
app.include_router(public_router, prefix="/api")  # sign in
signed_in = [Depends(current_actor)]  # everything else needs a signed-in user
app.include_router(auth_router, prefix="/api", dependencies=signed_in)
app.include_router(admin_router, prefix="/api", dependencies=signed_in)
app.include_router(router, prefix="/api", dependencies=signed_in)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


if STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="web")
