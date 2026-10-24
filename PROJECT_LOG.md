# ptrack — Project Log

> Personal, cross-platform "issue tracker for my life": tickets for myself + calendar events, in one place.
> ("ptrack" is a working codename — user isn't attached to it. See Q9.)
>
> **Status:** 🟢 Milestone 5 (reminders) done + pushed. Next: Milestone 6 (Debian deploy) planned for Monday night 2026-10-26 — see "Monday checklist". Repo: https://github.com/SSheffer1/ptrack
> **Last updated:** 2026-10-23

---

## How to use this file

- **Humans:** read *Summary*, *Open Questions*, and *Next Steps*. Everything else is reference.
- **Claude (future sessions):** read this whole file before doing anything in `ptrack/`. Then:
  - Append to the **Event Log** (newest at the bottom) for anything meaningful: research done, decisions made, code milestones, bugs, dead ends.
  - Record decisions in the **Decision Record** with an ID (`D-###`). Never silently change a decision — add a new one that supersedes it.
  - Move answered items out of **Open Questions** and into decisions.
  - Update **Status** and **Last updated** at the top.
  - Keep entries short. Link to files instead of pasting code.
  - The user wants to *understand* the system when done: explain new tech when introducing it, prefer boring/readable choices over clever ones.

---

## Summary

Goal: a single personal system that treats *tasks* like issue-tracker tickets (status, priority, labels, notes, history) and also handles *calendar events*, available on every device the user uses.

Current plan:
- **Already exists?** Partially (see *Prior Art*). Building is justified: user wants the result and to learn.
- **Tech exists?** Yes. Hard parts are offline sync and scope control.
- **Stack (proposed):** Svelte + TypeScript UI, packaged as an **Android APK via Capacitor** with a **local SQLite DB on the phone** (works fully offline) that syncs with a **Python/FastAPI server on the home Debian box**, exposed through **Caddy (HTTPS) on an opened port 443**. Desktop uses the same UI in a browser. Phone reminders are local notifications (no push server).

---

## User Profile (relevant to design)

- Desktop: Arch Linux. Phone: Android (iPhone optional, only if cheap).
- Home server: Debian on an AM4 APU machine, lots of RAM, otherwise unused; may host other services too.
- Prefers to avoid Tailscale; willing to open a port.
- Knows: Python, MATLAB, C++, HTML. Has learning resources for Java, Haskell, Nix. Willing to learn what's relevant.
- Priorities: working result > learning, but must understand the system in the end.
- Doesn't love Google Calendar. Standalone calendar preferred if good.

---

## Requirements

### Confirmed
- R1. Cross-platform: Linux desktop + Android (real APK) required; iOS nice-to-have.
- R2. Issue-tracker-style tickets for myself.
- R3. Calendar events — ptrack is the main calendar; Google is the fallback.
- R4. Single user now; possibly multiple users in the far future.
- R5. Extensible to other item types later.
- R6. Sync between devices via home server.
- R7. Offline use on the phone (read + edit, sync later).
- R12. One-time import of existing Google Calendar events — nice-to-have.

### Inferred (still unconfirmed)
- R8. Tickets with due dates show on the calendar.
- R9. Reminders / notifications on Android.
- R10. Fast capture (seconds, from phone or keyboard).
- R11. User owns the data; export in standard formats.

---

## Prior Art (as of mid-2026, from Claude's knowledge — not re-verified via web)

| Tool | Tickets | Calendar | Platforms | Self-host / own data | Fit notes |
|---|---|---|---|---|---|
| **TickTick** | Good (lists, tags, priority, subtasks) | Built-in calendar view, Google/Outlook sync | All incl. Linux (web/unofficial), mobile | No | Closest off-the-shelf match. Not issue-tracker flavored; premium for calendar features. |
| **Todoist** | Good | Calendar view + Google Calendar sync | All | No | Very polished capture; weaker as tracker. |
| **Notion** | Very flexible databases | Calendar views, Notion Calendar app | All | No | Can build exactly this, but slow, online-heavy. |
| **Linear** (free tier) | Excellent issue tracker | None really | Web/desktop/mobile | No | Great ticket UX, built for teams, no calendar. |
| **GitHub Issues + Projects** | Excellent | None | Web/mobile | No | Familiar to devs; no calendar, clunky for life stuff. |
| **Obsidian** + Tasks/Kanban/Full Calendar plugins | Decent | Via plugins | All | Yes (Markdown files) | Plain-text, owned data; plugin glue can be fragile. |
| **Logseq** | Decent | Journals, weak calendar | All | Yes | Outliner-first. |
| **Emacs Org-mode** (+ Orgzly/beorg on mobile) | Excellent (TODO states, tags, priorities, logging) | Agenda view | Desktop strong, mobile so-so | Yes (plain text) | Arguably the original "personal issue tracker + agenda". Steep learning curve. |
| **Vikunja** | Good (projects, kanban, labels) | CalDAV support | Web + PWA, self-hosted | Yes | Strong self-hosted candidate. |
| **Plane** | Linear-like | No | Web, self-hostable | Yes | Team-oriented, heavy for one person. |
| **Nextcloud Tasks + Calendar** | Basic | Yes (CalDAV) | All via DAVx⁵ / native | Yes | Standards-based; tasks UX is basic. |
| **Taskwarrior** (+ calcurse / khal) | Excellent CLI | Separate tool | CLI; mobile weak | Yes | Power-user, terminal-only. |
| **Akiflow / Sunsama / Motion** | Good | Strong time-blocking | All | No | Paid ($15–35/mo), productivity-coach flavored. |

**Takeaway:** TickTick, Obsidian+plugins, or Vikunja would cover most of this today. Building is justified by: issue-tracker semantics, a unified timeline, data ownership, and learning value.

---

## Feasibility / Tech Landscape (reference)

- **Cross-platform UI:** Tauri 2, Flutter, React Native/Expo, Capacitor, PWA.
- **Storage/sync:** local SQLite + sync layer (PowerSync, ElectricSQL, cr-sqlite, or hand-rolled); CRDTs (Automerge, Yjs, Loro); simple backend (PocketBase, Supabase, custom).
- **Standards:** iCalendar (RFC 5545) has `VEVENT` + `VTODO`; CalDAV serves them; ICS feeds are read-only subscriptions.
- **Calendar APIs:** Google Calendar API, Microsoft Graph.
- **Notifications:** local notifications on-device (work offline); Web Push / FCM need a server.
- **Risks:** sync conflicts/data loss, notification reliability (Android battery optimizers), scope creep, abandonment, security of a publicly exposed server.

### Options considered for the APK (D-010)
| Option | Language | Reuses web UI? | Notes |
|---|---|---|---|
| **Capacitor** ← chosen | TypeScript | Yes | Mature mobile wrapper; plugins for SQLite + local notifications; no new language. |
| Tauri 2 | TS + Rust | Yes | Also does desktop; mobile support newer; native bits need Rust. Fallback. |
| Flutter | Dart | No | Excellent, but separate UI + new language. |
| Native Kotlin | Kotlin/Java | No | Java resources help, but means 2 separate UIs. |

### Exposure options considered (D-011)
| Option | Opens ports? | Third party? | Notes |
|---|---|---|---|
| **Port 443 + Caddy + domain** ← chosen | Yes (443, maybe 80) | DNS provider only | Auto Let's Encrypt HTTPS; Caddy also routes other future services by subdomain. Needs public IPv4 (no CGNAT) or IPv6. |
| Self-hosted WireGuard | Yes (1 UDP port) | No | Most private; VPN app on phone; same "app must be on" downside as Tailscale. |
| Cloudflare Tunnel | No | Yes (Cloudflare sees traffic) | Works behind CGNAT. |
| Tailscale | No | Yes | User prefers to avoid. |

---

## Proposed Stack (pending user OK)

```
 Android phone (APK)                        Arch desktop
   Capacitor shell                            browser (same Svelte UI,
   ├─ Svelte + TypeScript UI                  online, served by server)
   ├─ local SQLite  ← works offline                  │
   ├─ local notifications (reminders)                │
   └─ sync engine ──────┐                            │
                        ▼  HTTPS :443                ▼
 Debian home server (Docker Compose)
   ├─ Caddy — reverse proxy + auto HTTPS; routes ptrack.<domain>, other services later
   ├─ ptrack-api: FastAPI (Python) — REST + /sync endpoint, auth
   ├─ SQLite file (or Postgres if multi-user happens) + nightly backups
   └─ /calendar.ics feed (optional, for Google/other calendars)
```

Why each piece:
- **Svelte + TypeScript UI** — closest modern framework to plain HTML; one UI for phone and desktop.
- **Capacitor** — wraps the web UI into a real APK; gives access to on-device SQLite and local notifications. Everything stays TypeScript on the client.
- **Local SQLite on phone** — the phone's copy is the source of truth while offline; the app never waits on the network.
- **Local notifications** — reminders are scheduled on the phone itself, so they fire offline and need no push server.
- **Sync (hand-rolled, D-012)** — every change is recorded with a timestamp + device ID. Phone pushes its changes and pulls everything newer than its last sync cursor. Conflicts resolve per field, last-write-wins. Simple enough to understand fully; fine for one user. Revisit (PowerSync/CRDT) only if real multi-user editing ever happens.
- **FastAPI backend** — Python, which the user knows; auto-generated API docs page.
- **SQLite on server** — single-user scale; tables carry `owner_id` from day one so multi-user later is a migration, not a rewrite (D-014).
- **Docker Compose + Caddy on Debian** — each service is a container; Caddy gives every service its own subdomain with HTTPS. Easy to add more self-hosted things later.
- **Desktop** — browser in v1 (online). Offline desktop (Tauri) is a later option.
- **iPhone** — technically possible with Capacitor, but needs a Mac + $99/yr Apple developer account to install. Out of scope unless that changes.

### Draft data model (sketch)
- `Item` — id (UUID, generated on device so offline creation works), owner_id, type (`ticket` | `event` | future), title, body (markdown), created/updated, deleted flag (soft delete — needed for sync)
- Ticket fields — status (backlog/todo/in-progress/blocked/done), priority, labels, due date, estimate, parent/children, links to other items
- Event fields — start, end, all-day, timezone, recurrence rule (RRULE), location, reminder offsets
- `Activity` — append-only history per item (status changes, comments) → issue-tracker feel
- `Project` / `Area` — grouping (e.g., Work, Home, Health); human-readable keys like `HOME-12`
- `Change` log — per-field changes with timestamp + device ID, drives sync

Note: human-readable keys (`HOME-12`) are tricky offline (two devices could both make `HOME-12`). Plan: device shows a temporary key; server assigns the final number on sync.

---

## v1 Scope (proposed)

1. Tickets: create/edit/close; title, markdown body, status, priority, labels, due date
2. Projects/areas with ticket keys (`HOME-12`)
3. Activity history + comments on tickets
4. ~~Events~~ → recurring tickets + optional due time (D-026)
5. Calendar views: month + agenda, showing ticket due dates
6. List + kanban board views with filters
7. Quick-add box (e.g. `fix bike !high #home due:fri`)
8. Android APK with offline use + sync to home server
9. Reminders as local notifications on Android
10. Server: Docker Compose + Caddy on Debian, HTTPS, login, nightly backup; desktop via browser

**Stretch / v1.1:** one-time Google Calendar import (.ics from Google Takeout), ICS feed out.
**Not in v1:** two-way Google sync, multi-user/sharing, offline desktop app, iOS, time tracking, attachments, CLI.

---

## Open Questions

- Q2c. Is the home connection behind CGNAT? User didn't know the term (explained 2026-10-21). Check: router admin page WAN IP vs https://ifconfig.me. Same → port forwarding works. Different, or WAN starts with `100.64–100.127.`, `10.`, `192.168.`, `172.16–31.` → CGNAT. If CGNAT: try IPv6, ask ISP for a public IP, or fall back to a cheap VPS relay / Cloudflare Tunnel (both add a dependency, which user dislikes).
- Q2f. Does the home IP change (dynamic)? If yes, need a DDNS updater for the domain (Caddy plugin or small cron job).
- Q2g. Who is the domain's DNS provider? (Affects DDNS + whether Caddy can use DNS challenge.)
- Q9. Better name than "ptrack"? (Codename is fine until then.)
- Q11. **User wants a single config file** for the choices listed in `CONFIGURATION.md` (e.g. `ptrack.toml` for the server + the in-app Settings page for per-device options) instead of constants spread across code. Keep CONFIGURATION.md updated whenever a setting changes or is added.
- Q12. Data created so far (incl. reminder-test tickets) is test data, not expected to carry over. Decide at Milestone 6: start the Debian server with a fresh DB, or copy this one.

---

## Monday checklist: Milestone 6 (Debian deploy)

Ask the user / have ready before starting:
1. Is Debian installed on the AM4 box? Can this laptop SSH into it (user, address)? Is it wired to the router?
2. DHCP reservation for the box in the Deco app (fixed address).
3. Domain: which DNS provider (Q2g)? Needed for a real HTTPS cert at home via Caddy's DNS-01 challenge (API token).
4. Home-only for now, or reachable from outside (port 443, homeowner approval)?
5. Fresh database or copy the laptop's (Q12)?
Plan: Docker + Compose on Debian; ptrack server image (uv, runs migrations on start); Caddy reverse proxy (HTTPS, room for other services); login (password, long-lived device tokens for phone/browser); nightly SQLite backup with rotation; phone app → https:// and drop `usesCleartextTraffic` (K8); fixes K11 (wired server).

---

## Resume here: Milestone 3 (Android APK) — DONE, kept for reference

**State when paused (2026-10-23):** all work committed + pushed (`fe7b77f`), except this log update. `~/Android/Sdk/cmdline-tools/latest` installed (verified). User was mid-install of `jdk21-openjdk android-tools` (sudo). Nothing Capacitor-related exists yet.

**Toolchain steps left**
1. Verify `java -version` → 21 (if several JDKs: `archlinux-java status`; Gradle needs 21, not 27). Verify `adb`.
2. `~/Android/Sdk/cmdline-tools/latest/bin/sdkmanager --sdk_root=$HOME/Android/Sdk --licenses` — the **user** must accept the licenses (interactive; suggest `! yes | …` only if they agree).
3. Install `platform-tools`, `platforms;android-<N>`, `build-tools;<N>.x` matching what Capacitor 8.5's android template asks for (check `android/variables.gradle` after `cap add`).
4. Point Gradle at the SDK via `app/android/local.properties` (`sdk.dir=/home/sheffy/Android/Sdk`, gitignored) rather than editing the user's shell profile.

**Planned design (proposed D-032; explain to user before building)**
- **Capacitor 8** wraps `app/` → `app/android/`. Plugins: `@capacitor/filesystem`, `@capacitor/app` (resume → sync), `@capacitor/network` maybe.
- **Local store = change log replay, in TypeScript** (instead of the SQLite plugin from D-012): device keeps every known change (server-confirmed + pending) in one JSON file in app-private storage (Filesystem, Directory.Data; write tmp + rename). Rows are rebuilt by replaying the log with per-field LWW — same rule as the server, order-independent. Reason: one language, no SQL duplicated from server, same code can later run in the desktop browser/Tauri; data is small (~2 MB for 1000 tickets). Must tell user this changes D-012.
- **Backend switch:** split `lib/api.ts` → `types.ts` (types, labels), `http.ts` (current fetch backend), `local/` (local backend + sync). `api.ts` re-exports types and picks the backend: native platform → local; browser → http (plus a dev flag to run local mode in the desktop browser for testing).
- **Local backend must mirror server semantics:** filters/sort/date ranges, key lookup, `assigned` effective date, comments, history from local log. Status → done also writes `completed_on` (local date) in the same batch (server keeps explicit values); reopen writes `completed_on: null`. **Ticket numbers and recurring next copies stay server-only** → appear after sync; UI already shows `…` for missing keys and links by id.
- **Sync engine:** device id `android-<uuid>` (not "web"/"server"); local clock `max(Date.now(), last+1)`, observes incoming ts (HLC-lite); outbox = this device's unconfirmed changes; `POST /sync {device_id, since, changes}` loop while `more`; dedupe on (entity_id, field, ts, device_id). Triggers: app start, resume, ~1 s after edits, every ~30 s. **A 400 rejects the whole batch forever** → validate locally (repeat rule: FREQ in DAILY/WEEKLY/MONTHLY/YEARLY, no COUNT/DTSTART) and offer "discard unsynced changes" in Settings.
- **Networking (LAN, HTTP):** run server with `--host 0.0.0.0` (fastapi dev binds 127.0.0.1); check Arch firewall. App's WebView origin is https://localhost → fetch to http://LAN is mixed content + CORS. Plan: enable `CapacitorHttp` (native HTTP, patches fetch → no CORS/mixed content) + allow cleartext in Android network config for dev builds. HTTPS via Caddy later removes the cleartext need.
- **UI:** Settings page (`#/settings`): server URL, device id, last sync, pending count, last error, Sync now, discard pending. Small sync indicator in top bar.
- **Tests:** add vitest for the local store/sync (fake transport), plus a real end-to-end run against the dev server.
- **Then:** `npx cap sync android`, `./gradlew assembleDebug`, install via `adb install` (USB debugging) or copy the APK to the phone.

---

## Known Issues / Tech Debt

- K1. Clock skew: LWW trusts device timestamps. A phone with a clock far in the future would win every conflict and push the server clock forward (`sync._observe`). Mitigation idea: reject/clamp ts too far ahead of server time.
- K2. Server clock (`sync._clock`) is in-memory; fine for one process, resets on restart (wall clock covers it).
- K3. Two devices creating the same project key offline → two projects with one key. REST blocks it; sync doesn't yet.
- K4. No auth — `OWNER_ID = "owner"` hardcoded in `api.py`. Must land before exposing to the internet (Milestone 6).
- K5. No migrations — `create_all` only. Add Alembic before there's data worth keeping. **Resolved 2026-10-23:** Alembic set up (D-030).
- K6. Moving a ticket between projects isn't supported (would need renumbering).
- ~~K7. Student email in author fields.~~ Fixed: repo-local git identity and `server/pyproject.toml` use `SSheffer1 <235915830+SSheffer1@users.noreply.github.com>` (GitHub private address, since repo is public). Global git config untouched (school identity for other repos).

---

## Decision Record

| ID | Date | Decision | Rationale | Status |
|---|---|---|---|---|
| D-001 | 2026-10-21 | Project lives in `~/Projects/ptrack`; this file is the running log. | Directory already existed, empty. | Active |
| D-002 | 2026-10-21 | Build (not adopt). Architecture A: PWA + home server. | User values result + learning; home server; Android primary. | Superseded by D-009 |
| D-003 | 2026-10-21 | Backend: Python + FastAPI + SQLite (SQLModel/SQLAlchemy). | User knows Python; single-user scale; easy backup. | Proposed |
| D-004 | 2026-10-21 | Frontend: Svelte + TypeScript, installable PWA. | Closest to HTML; one codebase. | Superseded by D-010 |
| D-005 | 2026-10-21 | Networking: Tailscale. | User unsure about ports. | Superseded by D-011 |
| D-006 | 2026-10-21 | ptrack is the primary calendar; use an existing calendar UI component. | User dislikes Google Calendar. | Proposed |
| D-007 | 2026-10-21 | Google integration = read-only ICS feed; two-way sync deferred. | Two-way sync is the biggest complexity sink. | Proposed (now stretch) |
| D-008 | 2026-10-21 | Online-first in v1. | Avoid sync complexity. | Superseded by D-012 |
| D-009 | 2026-10-21 | Build. Local-first Android app + home server; desktop via browser. | User wants a real APK with offline use. | Proposed |
| D-010 | 2026-10-21 | Client: Svelte + TypeScript UI, packaged as APK with Capacitor; same UI served to desktop browser. | Reuses one UI; stays in TypeScript; mature SQLite/notification plugins. | Proposed |
| D-011 | 2026-10-21 | Exposure: open port 443, Caddy reverse proxy with auto HTTPS. | User prefers ports over Tailscale; Caddy also hosts future services. Depends on Q2c/Q2d. | Proposed |
| D-012 | 2026-10-21 | Offline-first on phone from day one: local SQLite + hand-rolled sync (change log, per-field last-write-wins). | Retrofitting offline later is much harder; hand-rolled is understandable. | Proposed |
| D-013 | 2026-10-21 | Reminders via on-device local notifications. | Work offline; no push server. | Proposed |
| D-014 | 2026-10-21 | Single-user v1, but `owner_id` on all tables. | Cheap now; makes future multi-user a migration. | Proposed |
| D-015 | 2026-10-21 | Server deploy: Docker Compose on Debian. | Machine will host multiple services. | Proposed |
| D-016 | 2026-10-21 | Desktop: browser-only in v1; real desktop app later (likely Tauri wrapping the same Svelte UI, with local SQLite reusing the phone's sync code). | User OK with browser for v1 but wants a real app eventually. | Proposed |
| D-018 | 2026-10-21 | Early build/test is LAN-only; public exposure (port 443) later, once homeowner approves. For HTTPS on LAN, prefer a real cert via Caddy DNS-01 challenge on a subdomain pointing at the server's LAN IP (needs DNS provider API, Q2g); fallback is plain HTTP with Android cleartext allowed for dev builds only. | Port forward pending homeowner approval; LAN-first lets work start now. | Active |
| D-019 | 2026-10-21 | Ticket keys are per-project prefix + sequence (`HOME-12`), never reused; offline-created tickets get a temp key until server assigns the number on sync. | User confirmed. | Active |
| D-020 | 2026-10-21 | v1 scope accepted as listed in *v1 Scope*. | User approved. | Active |
| D-021 | 2026-10-21 | Python tooling: uv (pyproject.toml + uv.lock), pytest. Installed on Arch via `pacman -S uv`; Docker image brings its own. | One tool instead of pip/venv/pip-tools/pyenv; lockfile reproducibility; standard pyproject so easy to leave. | Active |
| D-022 | 2026-10-21 | All writes (web REST and phone sync) become field-level changes in one `change` table, applied via `sync.apply_changes`. Ticket history = change log; comments are their own synced entity. No separate Activity table. | One write path, complete history for free, fewer tables to sync. | Active |
| D-023 | 2026-10-21 | Sync protocol v0: `POST /sync {device_id, since, changes[]}` → `{changes, cursor, more}`. Device ts must strictly increase per device. Server-only fields: id, owner_id, created_at, updated_at, number, next_number. Batches are all-or-nothing; retries are deduped on (entity_id, field, ts, device_id). | Simple, idempotent, testable. | Active |
| D-024 | 2026-10-23 | Code hosted on GitHub as public repo `SSheffer1/ptrack`, branch `master`. Commit identity: GitHub noreply address. This log is committed too, so keep secrets/IPs out of it. | User wants it on GitHub, public; noreply hides real email from scrapers. | Active |
| D-025 | 2026-10-23 | Web app: plain Svelte 5 + Vite + TypeScript (not SvelteKit), hash routing (`#/items/HOME-12`), flat `app/src/` layout. API moved under `/api`; server also serves `app/dist` at `/` when built (`PTRACK_STATIC`). Dev: Vite on :5173 proxies `/api` → :8000. | SvelteKit's SSR/routing adds concepts we don't need; static SPA drops straight into Capacitor later; hash routing needs no server config. | Active |
| D-026 | 2026-10-23 | **Calendar is a view of the tracker**, not a separate event system. Calendar shows items by due date (+ optional due time, e.g. exam Wed 10:00). No start/end time blocks, no lectures/class schedule — those stay out of ptrack. Recurrence = recurring *tickets* (marking done creates the next one, e.g. weekly lab report). Google Calendar integration dropped from v1; optional one-way ICS export later. | User: standalone app; calendar should reflect tracker issues; "lectures don't need to be on the tracker, assignment due dates are reasonable". Supersedes Google parts of D-006/D-007 and the 'events' item type. | Active |
| D-027 | 2026-10-23 | Milestone order: M4 (due times + calendar + recurring tickets) before M3 (Android APK). | Desktop already useful; APK then wraps the finished UI incl. calendar. | Active |
| D-028 | 2026-10-23 | Recurring tickets: `repeat` = RRULE (no DTSTART; due date is the start; COUNT rejected, use UNTIL). Server spawns the next copy when status → done (applied change), copying project/title/body/priority/labels/due_time/repeat; sets `next_id` on the original (server-only field) so re-completing doesn't duplicate. Next due = next occurrence after old due; if that's in the past, first occurrence ≥ today. Uses python-dateutil. UI presets are weekday-agnostic ("Every week" follows the due date). | Server authority avoids duplicate spawns from multiple devices; standard RRULE keeps ICS export easy. | Active |
| D-029 | 2026-10-23 | Assigned/completed dates. `assigned_on` (user-settable; null → created date; API returns effective `assigned`). `completed_on` (date): server sets it from the *change's* ts when status → done (so offline completions get the right day), clears on reopen, unless the same batch set `completed_on` explicitly; user can edit it. List `sort` = created / due / completed. Server-set completed_on hidden from UI history. | User: "created date is fine for assigned... optionally whenever I say... same for completion". | Active |
| D-030 | 2026-10-23 | Schema migrations with Alembic, inside the package (`src/ptrack/migrations`), `render_as_batch` for SQLite; server runs `upgrade head` on startup; `test_migrations` asserts migrations == models. Autogenerate against a scratch DB via `PTRACK_DB`. | Real data in dev DB now; no more hand ALTERs. | Active |
| D-031 | 2026-10-23 | Calendar shows finished tickets on their `completed_on` day (fallback: due), struck through, after that day's open items, regardless of the Done status chip; chips filter open tickets only. API: `completed_from`/`completed_to`. | User: closed tickets disappeared from the calendar; wanted them on the day done with strikethrough. | Active |
| D-032 | 2026-10-23 | Phone storage = change log replayed in TypeScript (`app/src/lib/local/`: store.ts LWW log + rows, backend.ts mirrors REST semantics, sync.ts engine, persist.ts one JSON file via Capacitor Filesystem, tmp+rename). Supersedes SQLite part of D-012. `runtime.svelte.ts` picks backend: native → local, browser → http unless the Settings "offline-first mode" test switch is on. Views re-fetch on `runtime.dataVersion`. Device ids `android-<uuid>` / `browser-<uuid>`. Sync: start, every 30 s, 1 s after edits, on app resume. Server 400 → sync paused until user discards pending. CapacitorHttp handles fetch on Android (no CORS/mixed content). | User: "do it, sounds simpler even". | Active |
| D-017 | 2026-10-21 | No Tailscale/third-party tunnel unless forced by CGNAT. Use user's own domain + port forward + Caddy. | User objects to extra moving parts and dependencies. | Active |

---

## Event Log

- **2026-10-21** — Project kicked off. User described goal: cross-platform personal issue tracker + calendar. Claude surveyed prior art and tech feasibility (from model knowledge, no live web search yet), drafted three candidate architectures and a data model sketch, and created this log. `ptrack/` was empty.
- **2026-10-21** — User answered Q1/Q2/Q3/Q5/Q6: Android (iOS optional), home server OK (ports uncertain), standalone calendar preferred if good else Google, goal > learning but must understand it, knows Python/C++/HTML/MATLAB with resources for Java/Haskell/Nix. Claude proposed stack D-002..D-008 (PWA + Tailscale) and a v1 scope.
- **2026-10-21** — User: server is Debian on AM4 APU (multi-service), prefers to avoid Tailscale (will open port), wants a real APK with offline use, single-user now / maybe multi-user far future, Google import nice-to-have, dislikes name "ptrack". Claude revised plan: Capacitor APK + local SQLite + hand-rolled sync, Caddy on 443, Docker Compose (D-009..D-015). Superseded D-002/004/005/008. Offline + APK moved into v1 scope; Google import → stretch; iOS → out (needs Mac + Apple dev account).
- **2026-10-21** — User: already owns a domain; Tailscale objection = extra moving parts + dependency (D-017); browser-only desktop OK for v1, real desktop app later (D-016); didn't know what CGNAT means (explained, Q2c still open). User stepped away before reviewing v1 scope (Q7). **Resume here:** get Q2c result + Q7 answer, then start Next Steps #3.
- **2026-10-21** — User: port opening likely fine, pending homeowner approval; first build/test rounds will be LAN-only (D-018). Q2c (CGNAT) deferred until going public. Still waiting on Q7 (scope).
- **2026-10-21** — Walked user through scope item 6 (list + kanban + filters + saved views); user OK with it as proposed. Explained ticket keys (`HOME-12`). Rest of Q7 still open.
- **2026-10-21** — User confirmed project-prefixed ticket keys (D-019) and said the plan sounds good → v1 scope accepted (D-020). Planning phase essentially done; Q2g (DNS provider) and Q9 (name) don't block coding.
- **2026-10-21** — Explained uv; user agreed (D-021). Dev machine has Python 3.14.8, no uv/pip yet — user to run `sudo pacman -S uv`. Ran `git init` (branch `master`), added README.md + .gitignore. Nothing committed yet (commit only when user asks). **Next:** once uv is installed, `uv init` in `server/` and start Milestone 1.
- **2026-10-21** — **Milestone 1 done (uncommitted).** uv 0.13.4 installed. `server/` created (Python 3.14, FastAPI, SQLModel, pytest). Implemented: tables (`models.py`), change log + per-field LWW + server-assigned ticket numbers + simplified HLC (`sync.py`), REST API for projects/tickets/comments/history + `POST /sync` (`api.py`). REST writes go through the same change path as sync (D-022). 21 tests pass; smoke-tested real server with curl. Design deviations from sketch: no separate `Activity` table — history *is* the change log (D-022); event-only fields deferred to Milestone 4; no project PATCH/rename endpoint yet. See *Known Issues*.
- **2026-10-23** — Session resumed after a few days. User installed + logged into `gh` (account SSheffer1, git protocol ssh). Set repo-local identity to SSheffer1 + noreply email, made first commit, created public GitHub repo and pushed (D-024). Push gotcha: default key `~/.ssh/id_ed25519` belongs to a different GitHub account; the key registered to SSheffer1 is `~/.ssh/thinkarchshr` (GitHub title "thinkarch"). Fixed repo-locally with `git config core.sshCommand "ssh -i ~/.ssh/thinkarchshr -o IdentitiesOnly=yes"` (global SSH config untouched). **Next:** walk user through what Milestone 1 does (they want to look at it), then Milestone 2.

---

## Next Steps

1. ~~Scope + stack confirmed.~~ Still open but non-blocking: Q2g (DNS provider, needed for LAN HTTPS), Q9 (name), Q2c (CGNAT, before going public).
2. Optional: web check that Capacitor SQLite/notification plugins and calendar component candidates are current.
3. ~~`git init`, README, repo layout, dev environment.~~ Done (`app/`, `deploy/` created when needed).
4. ~~Milestone 1: data model + change log + CRUD/sync API on server, with tests.~~ Done 2026-10-21.
5. ~~Milestone 2: Svelte UI (ticket list + detail) running in desktop browser against server.~~ Done 2026-10-23.
6. ~~Milestone 4 (moved up, D-027): due times + calendar view (month + agenda) + recurring tickets.~~ Done 2026-10-23 (+ assigned/completed dates, migrations).
7. ~~Milestone 3: Capacitor APK with local SQLite + sync; test offline edits on phone.~~ Done 2026-10-24 (change-log store instead of SQLite, D-032).
8. ~~Milestone 5: reminders.~~ Done 2026-10-24 (phone-only local notifications).
9. Milestone 6 (Mon 2026-10-26): deploy on Debian (Docker Compose + Caddy) + HTTPS + login + backups. Remaining v1 after that: kanban board, quick-add.
