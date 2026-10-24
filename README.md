# ptrack

**A self-hosted issue tracker for your life.** Track homework, chores and projects as
tickets, see their due dates on a calendar, and get reminded on your phone, with an
Android app that works offline and syncs to a server you run at home.

> "ptrack" is a working name.

## Features

- **Tickets like an issue tracker.** Projects with keys (`HOME-12`), statuses
  (Backlog → To do → In progress → Blocked → Done), priorities, labels, Markdown
  descriptions, comments, and a full history of every change.
- **Calendar and agenda.** Due dates (with optional times) on a month calendar and a
  day-by-day agenda; finished tickets stay visible, struck through, on the day you did them.
- **Repeating tickets.** "Every Friday", "every 2 weeks", "monthly"… Mark one done and the
  next copy appears with the next due date.
- **Assigned and completed dates.** Recorded automatically, editable when you entered
  something late, and shown as "2 days early" / "1 day late".
- **Phone reminders.** Notifications scheduled on the phone itself, so they work offline and
  with the app closed. Default: 8 hours before a timed ticket, 9 AM on the day otherwise.
- **Offline-first Android app.** The phone keeps its own copy of your data; edits made offline
  sync when it reaches the server again.
- **Your data, your server.** One small Python server and a single SQLite file. No accounts
  anywhere else, nothing sent to third parties.
- **Family sharing** *(in progress)*. Accounts for family members, shared projects with
  owners and editors, and tickets assigned to each other.

## How it works

```
 Android app (offline-first)          Desktop browser
   own copy of the data                  │
   └── syncs ────────────┐               │
                         ▼               ▼
              ptrack server (FastAPI + SQLite) on your home server
```

Every edit is stored as a small change ("set the status of HOME-12 to Done at 14:02, from
the phone"). The server keeps the log of all changes; each device downloads the changes it
hasn't seen. When two devices edit the same field, the later edit wins; edits to different
fields never conflict. See [docs/PROJECT_LOG.md](docs/PROJECT_LOG.md) for the design
decisions behind this.

| Path | What |
|---|---|
| `server/` | Python API and sync server: FastAPI, SQLModel, SQLite, Alembic migrations |
| `app/` | Svelte 5 + TypeScript web app, packaged for Android with Capacitor |
| `docs/` | Design log and the list of every adjustable setting |

## Status

Early, and working. In daily use on one Android phone and a Linux desktop. The first
release (v1.0) will add family accounts, HTTPS and a one-command Docker setup for a home
server. Until then, setup is the development setup below.

## Development setup

Requirements: [uv](https://docs.astral.sh/uv/), Node.js 20+, and for the Android app a
JDK 21 and the Android SDK command-line tools.

```bash
# Server: http://localhost:8000 (API docs at /docs)
cd server
uv run ptrack-admin create-user yourname --admin   # first account
uv run fastapi dev src/ptrack/main.py              # add --host 0.0.0.0 for the phone

# Web app: http://localhost:5173 (talks to the server above)
cd app
npm install
npm run dev

# Tests
(cd server && uv run pytest)
(cd app && npm test && npm run check)

# Android debug build, installed over USB (adb)
cd app
npm run build && npx cap sync android
(cd android && ./gradlew assembleDebug)
adb install -r android/app/build/outputs/apk/debug/app-debug.apk
```

In the app, open Settings and enter your server's address, e.g. `http://192.168.1.20:8000`.

More detail: [server/README.md](server/README.md) (migrations, admin commands) and
[docs/CONFIGURATION.md](docs/CONFIGURATION.md) (every adjustable setting and where it lives).

## License

Copyright © 2026 SSheffer1

ptrack is free software: you can redistribute it and/or modify it under the terms of the
GNU General Public License as published by the Free Software Foundation, either version 3
of the License, or (at your option) any later version. It is distributed in the hope that
it will be useful, but WITHOUT ANY WARRANTY; see [LICENSE](LICENSE) for details.
