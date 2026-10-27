# ptrack configuration

ptrack's settings come in three kinds:

1. **Server settings**, in `server/ptrack.toml`, for whoever runs the server.
2. **Personal preferences**, set by each person in the app (Settings → Preferences)
   and synced to all their devices.
3. **Built-in behavior**, fixed in the code. Changing these means changing the code.

Paths are relative to the repo root. "Both" means the server and the app each have
a copy that must match (the app needs it to work offline).

## 1. Server settings (`server/ptrack.toml`)

Copy `server/ptrack.example.toml` to `server/ptrack.toml` and edit it; anything
left out uses the default. `uv run ptrack-admin show-config` prints what's in
effect. Loaded by `server/src/ptrack/config.py`; unknown or misspelled settings
are an error. Environment variables `PTRACK_CONFIG` (which file), `PTRACK_DB` and
`PTRACK_STATIC` override the file.

| Setting | Default | What it does |
|---|---|---|
| `[server] host` | `127.0.0.1` | `0.0.0.0` makes the server reachable from phones on the network |
| `[server] port` | `8000` | |
| `[server] static_dir` | `app/dist` in this checkout | the built web app served at `/` |
| `[database] url` | `sqlite:///ptrack.db` | where the data lives |
| `[accounts] min_password_length` | `8` | |
| `[accounts] login_delay_seconds` | `1` | pause after a wrong password, to slow down guessing |
| `[accounts] device_idle_days` | `0` (never) | sign out devices unused for this many days |
| `[sync] page_size` | `1000` | changes per sync response |
| `[backup] enabled` | `true` | nightly copies of the database (SQLite only) |
| `[backup] dir` | a `backups` folder next to the database | where the copies go (in Docker: `/data/backups`, inside the data volume) |
| `[backup] hour` | `3` | when, in the server's local time (Docker uses the host's time zone) |
| `[backup] keep_days` | `14` | older copies are deleted; the newest is always kept |

Accounts themselves are managed with `uv run ptrack-admin …` (see
[server/COMMANDS.md](../server/COMMANDS.md)) or in the app (Settings → Family
accounts, for admins).

## 2. Personal preferences (in the app)

Each person sets their own in Settings → Preferences. They're saved as you change
them and synced like tickets, but only to your own devices. Defaults and the code
that uses them: `app/src/lib/prefs.svelte.ts`. The server checks and stores them:
`server/src/ptrack/prefs.py` (both).

| Preference | Default | Affects |
|---|---|---|
| Default reminders | at the due time | tickets with a due date whose reminders you haven't picked, with or without a due time (one default for both since D-048; the old separate timed/untimed settings are ignored) |
| Untimed tickets are due at | 9 AM | when reminders for untimed tickets count from |
| Weeks start on | Sunday | the month calendar |
| Due dates turn orange | 2 days ahead | list, agenda, calendar, ticket page |
| Statuses shown when the app opens | all except Done | the Status filter's starting state (list, agenda and calendar) |
| List sorted by | Newest last | the List view's starting sort (also: due date, recently completed, project, priority, status, title) |
| Sync in the background | every 5 minutes | the phone app (offline-first devices); "never" leaves syncing to edits, opening the app, and Sync now |

Per device (not synced): the **server address**, entered when signing in on the
phone, and the browser-only **offline-first test mode** switch.

## 3. Built-in behavior

### Reminders

| Behavior | Value | Where |
|---|---|---|
| One-tap reminder choices (timed) | at due time, 1 h, 8 h, 1 day, 2 days, 1 week before | `app/src/lib/reminders.ts` `reminderChoices` |
| One-tap reminder choices (untimed) | on the day, day before, 2 days, 1 week before | same |
| Offset format | `0` or `-<n>m/h/d` (up to 4 digits) | both: `server/src/ptrack/reminders.py`, `app/src/lib/reminders.ts` `OFFSET_RE` |
| Specific-time format | `@YYYY-MM-DDTHH:MM`, phone's local time; works without a due date, not allowed as a default | same, `AT_RE` |
| Who gets a ticket's reminders | the assignee, or the creator if unassigned | both: `server/src/ptrack/sync.py` `notified_user`, `app/src/lib/types.ts` `notifiedUser` |
| Max reminders scheduled on a phone | 50 (soonest first) | `app/src/lib/reminders.ts` `upcomingReminders` |
| Where notifications appear | the Android app only | `app/src/lib/runtime.svelte.ts` |

### Recurring tickets

| Behavior | Value | Where |
|---|---|---|
| Repeat presets | every day / weekday (Mon–Fri) / week / 2 weeks / month / year | `app/src/lib/recurrence.ts` `REPEAT_PRESETS` |
| Finished late → next due date | first occurrence from today on (skips missed ones) | `server/src/ptrack/recurrence.py` `next_due` |
| Copied to the next copy | project, title, description, priority, labels, due time, repeat, reminders (specific times move by as many days as the due date), assignee, creator | `server/src/ptrack/sync.py` `RECURRING_FIELDS`, `reminders.py` `shift_reminders` |
| `COUNT=` in rules | rejected (use `UNTIL=`) | both: `recurrence.py` `normalize_rule`, `app/src/lib/local/backend.ts` `checkRepeat` |

### Tickets, projects and sharing

| Behavior | Value | Where |
|---|---|---|
| Statuses | Backlog, To do, In progress, Blocked, Done | both: `server/src/ptrack/models.py` `Status`, `app/src/lib/types.ts` `STATUSES` |
| Priorities | No priority, Low, Medium, High, Urgent | both: `models.py` `Priority`, `types.ts` `PRIORITIES` |
| New ticket defaults | To do, no priority, no labels, unassigned | `server/src/ptrack/api.py` `ItemCreate`, `backend.ts` `createItem` |
| Project keys | 1–10 chars, A–Z and 0–9, starting with a letter; unique on the server; offline clashes become GYM → GYM2 | both: `api.py`, `backend.ts`; `sync.py` `_resolve_key_conflicts` |
| Roles | owner: everything; editor: create, edit, comment on tickets; a server admin who is a member may also delete tickets | both: `sync.py` `_check_permission`, `backend.ts` |
| "Assigned" date | the day the ticket was created, unless set | `api.py` `_read`, `backend.ts` `toItem` |
| Completion date | the day it's marked done; cleared when reopened | `sync.py` `_update_completion_dates`, `backend.ts` `updateItem` |
| Calendar: finished tickets | shown when the Status filter includes Done, struck through, on the day completed | `app/src/CalendarMonth.svelte` |
| Date/time formats, light/dark theme | follow the device | `app/src/lib/format.ts`, `app/src/app.css` |

### Accounts

| Behavior | Value | Where |
|---|---|---|
| Who creates accounts | admins only (no sign-up) | `server/src/ptrack/auth.py`, `admin.py` |
| Username format | lowercase letters, digits, `. _ -`; 2–32 chars, starting with a letter | `auth.py` `USERNAME_PATTERN` |
| Password hashing | scrypt, N=2^14, r=8, p=1 | `auth.py` `SCRYPT_N/R/P` |
| Signing out a device | removes that device's copy of the data the next time it connects | `app/src/lib/runtime.svelte.ts` `forgetSession` |

### Sync timing (phone app)

| Behavior | Value | Where |
|---|---|---|
| Sync | on start, 1 s after an edit, when you switch back to the app, with the Sync now button, and in the background per your preference | `app/src/lib/runtime.svelte.ts` |
| Save to the phone's storage | 300 ms after an edit | same, `SAVE_AFTER_EDIT_MS` |
| Re-plan reminders | 2 s after any change | same, `RESCHEDULE_AFTER_MS` |
| Conflicts | latest edit wins, per field | both: `server/src/ptrack/sync.py`, `app/src/lib/local/store.ts` |

### Android app

| Behavior | Value | Where |
|---|---|---|
| App id / name | `io.github.ssheffer1.ptrack` / ptrack | `app/capacitor.config.ts` |
| Icon | the P-trap with a mouse, on #3b5bdb | sources in `app/icon/` (`build.sh` renders the PNGs); adaptive icon: `app/android/app/src/main/res/drawable/ic_launcher_foreground.xml` |
| Plain HTTP allowed | yes, until the server has HTTPS | `app/android/app/src/main/AndroidManifest.xml` `usesCleartextTraffic` |
| Android versions | 7.0 (SDK 24) and up, targets 16 (SDK 36) | `app/android/variables.gradle` |
