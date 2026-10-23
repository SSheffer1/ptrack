# ptrack

A personal issue tracker + calendar: tickets for yourself and calendar events in one place,
with an offline-capable Android app that syncs to a self-hosted server.

> Working codename. Planning notes, decisions, and progress live in [PROJECT_LOG.md](PROJECT_LOG.md).

## Layout

| Path | What |
|---|---|
| `server/` | Python (FastAPI + SQLite) API and sync server |
| `app/` | Svelte + TypeScript UI, packaged for Android with Capacitor |
| `deploy/` | Docker Compose + Caddy config for the Debian home server |

## Status

Early development — see [PROJECT_LOG.md](PROJECT_LOG.md).
