# ptrack configuration

Every choice that's currently configured, where it lives, and its current value.
To change one, ask: "change <setting> to <value>".

> **Future wish:** put these in a single config file (e.g. `ptrack.toml` for the
> server, plus the in-app Settings screen for per-device options) instead of
> having them spread across code. Tracked in PROJECT_LOG.md (Q11).

Paths are relative to the repo root. "Both" means the server and the app each
have a copy that must match (the app needs it to work offline).

## Reminders

| Setting | Current value | Where |
|---|---|---|
| Default reminder, ticket with a due time | 8 hours before (`-8h`) | `app/src/lib/reminders.ts` `defaultReminders` (+ docstring in `server/src/ptrack/reminders.py`) |
| Default reminder, ticket without a time | 9:00 AM on the due day (`0`) | same |
| Hour used for "due" on untimed tickets | 9 (9:00 AM) | `app/src/lib/reminders.ts` `UNTIMED_HOUR` |
| One-tap reminder choices (timed) | at due time, 1 h, 8 h, 1 day, 2 days, 1 week before | `app/src/lib/reminders.ts` `reminderChoices` |
| One-tap reminder choices (untimed) | 9 AM on the day, day before, 2 days, 1 week before | same |
| Allowed offset format | `0` or `-<n>m/h/d` (up to 4 digits) | both: `server/src/ptrack/reminders.py` `OFFSET_RE`, `app/src/lib/reminders.ts` `OFFSET_RE` |
| Max reminders scheduled on the phone at once | 50 (soonest first) | `app/src/lib/reminders.ts` `upcomingReminders(limit)` |
| Delay before re-planning reminders after a change | 2 s | `app/src/lib/runtime.svelte.ts` `RESCHEDULE_AFTER_MS` |
| Where notifications appear | phone only | `app/src/lib/runtime.svelte.ts` (`runtime.native` check) |

## Recurring tickets

| Setting | Current value | Where |
|---|---|---|
| Repeat presets | every day / weekday (Mon–Fri) / week / 2 weeks / month / year | `app/src/lib/recurrence.ts` `REPEAT_PRESETS` |
| Finished late → next due date | first occurrence from today on (skips missed ones) | `server/src/ptrack/recurrence.py` `next_due` |
| Fields copied to the next copy | project, title, description, priority, labels, due time, repeat, reminders | `server/src/ptrack/sync.py` `RECURRING_FIELDS` |
| `COUNT=` in rules | rejected (use `UNTIL=`) | both: `recurrence.py` `normalize_rule`, `app/src/lib/local/backend.ts` `checkRepeat` |

## Tickets and projects

| Setting | Current value | Where |
|---|---|---|
| Statuses | Backlog, To do, In progress, Blocked, Done | both: `server/src/ptrack/models.py` `Status`, `app/src/lib/types.ts` `STATUSES` / `STATUS_LABELS` |
| Priorities | No priority, Low, Medium, High, Urgent | both: `models.py` `Priority`, `types.ts` `PRIORITIES` / `PRIORITY_LABELS` |
| New ticket defaults | status To do, priority none, no labels | `server/src/ptrack/api.py` `ItemCreate`, `app/src/lib/local/backend.ts` `createItem` |
| Project key format | 1–10 chars, A–Z and 0–9, starts with a letter | both: `api.py` `ProjectCreate`, `backend.ts` `PROJECT_KEY_RE` |
| "Assigned" date default | the day the ticket was created | `api.py` `_read`, `backend.ts` `toItem` |
| Completion date | set to the day it's marked done, cleared when reopened | `server/src/ptrack/sync.py` `_update_completion_dates`, `backend.ts` `updateItem` |

## Views

| Setting | Current value | Where |
|---|---|---|
| Statuses shown by default | everything except Done | `app/src/lib/state.svelte.ts` `filters.statuses` |
| Default list sort | Newest last (by created) | `app/src/lib/state.svelte.ts` `filters.sort` |
| Calendar: finished tickets | always shown, struck through, on the day completed | `app/src/CalendarMonth.svelte` `load` |
| Calendar week starts on | Sunday | `app/src/CalendarMonth.svelte` `WEEKDAYS` + `days` |
| Due date turns orange ("soon") | 2 days or less away | `app/src/lib/format.ts` `dueTone` |
| Date/time formats | your device's locale | `app/src/lib/format.ts` |
| Light/dark theme | follows the system setting | `app/src/app.css` (`prefers-color-scheme`) |

## Sync (phone app)

| Setting | Current value | Where |
|---|---|---|
| Server address | set per device in the app's Settings page | stored in the app's `files/ptrack.json` |
| Sync every | 30 s while open, plus on app start and when you switch back to it | `app/src/lib/runtime.svelte.ts` `SYNC_EVERY_MS` |
| Sync after an edit | 1 s later | same, `SYNC_AFTER_EDIT_MS` |
| Save to storage after an edit | 300 ms later | same, `SAVE_AFTER_EDIT_MS` |
| Changes per sync page | 1000 | `server/src/ptrack/api.py` `SYNC_PAGE_SIZE` |
| Conflict rule | latest edit wins, per field | `server/src/ptrack/sync.py`, `app/src/lib/local/store.ts` |

## Server

| Setting | Current value | Where |
|---|---|---|
| Database file | `server/ptrack.db` | env `PTRACK_DB` (default `sqlite:///ptrack.db`), `server/src/ptrack/db.py` |
| Built web app it serves | `app/dist` | env `PTRACK_STATIC`, `server/src/ptrack/main.py` |
| Address / port | `0.0.0.0:8000` (all interfaces) | command line: `uv run fastapi dev src/ptrack/main.py --host 0.0.0.0` |
| User | single user `owner`, no login yet | `server/src/ptrack/api.py` `OWNER_ID` (login: Milestone 6) |
| Firewall | ufw allows 8000/tcp from `the home subnet` | laptop's ufw rules (`sudo ufw status`) |

## Android app

| Setting | Current value | Where |
|---|---|---|
| App id / name | `io.github.ssheffer1.ptrack` / ptrack | `app/capacitor.config.ts` |
| Icon | Capacitor default | `app/android/app/src/main/res/mipmap-*` |
| Plain HTTP allowed | yes (until HTTPS, Milestone 6) | `app/android/app/src/main/AndroidManifest.xml` `usesCleartextTraffic` |
| Android versions | min 7.0 (SDK 24), target 16 (SDK 36) | `app/android/variables.gradle` |

## Development

| Setting | Current value | Where |
|---|---|---|
| Dev web server | Vite on :5173, forwards `/api` to `localhost:8000` | `app/vite.config.ts` |
| Git identity (this repo) | `SSheffer1 <235915830+SSheffer1@users.noreply.github.com>` | `.git/config` (repo-local, not committed) |
| SSH key for pushes | `~/.ssh/github-key` | `.git/config` `core.sshCommand` |
