# ptrack server image: the Python API plus the built web app, in one container.
# Built from the repo root:  docker compose -f deploy/compose.yaml build
#
# Three stages, so the final image carries no Node or build tools:
#   web    - Node builds the Svelte app into static files
#   python - uv installs the server and its exact locked dependencies into a venv
#   final  - plain Python + that venv + the web files, running as a normal user

FROM node:24-trixie-slim AS web
WORKDIR /app
COPY app/package.json app/package-lock.json ./
RUN npm ci
COPY app/ ./
RUN npm run build

FROM ghcr.io/astral-sh/uv:0.13-python3.14-trixie-slim AS python
# Use the image's Python (same as the final stage), copy files instead of linking.
# Build the venv at /venv, the same path it has in the final image (its scripts
# have that path written into them).
ENV UV_PYTHON_DOWNLOADS=0 UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1 UV_PROJECT_ENVIRONMENT=/venv
WORKDIR /server
# Dependencies first: this layer is reused until uv.lock changes.
COPY server/pyproject.toml server/uv.lock server/.python-version ./
RUN uv sync --frozen --no-dev --no-install-project
COPY server/ ./
RUN uv sync --frozen --no-dev --no-editable

FROM python:3.14-slim-trixie
RUN useradd --create-home --uid 1000 ptrack && mkdir /data && chown ptrack /data
COPY --from=python /venv /venv
COPY --from=web /app/dist /web
COPY deploy/ptrack.toml /etc/ptrack.toml
ENV PATH=/venv/bin:$PATH PTRACK_CONFIG=/etc/ptrack.toml
USER ptrack
WORKDIR /data
EXPOSE 8000
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health')"
CMD ["ptrack-serve"]
