"""Run the server for real (no auto-reload), using ptrack.toml.

    uv run ptrack-serve

For development, `uv run fastapi dev src/ptrack/main.py` reloads on every save.
"""

import uvicorn

from .config import settings


def main() -> None:
    uvicorn.run("ptrack.main:app", host=settings.host, port=settings.port, proxy_headers=True)
