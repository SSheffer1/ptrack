# ptrack — Project Log

> Personal, cross-platform "issue tracker for my life": tickets for myself + calendar events, in one place.
> Product name: **PTrack** (D-041). Code-level names stay lowercase `ptrack`.
>
> **Status:** 🟡 Server box is up and **running ptrack in testing** (Debian 13, wired, managed from the laptop over SSH; plain HTTP via Caddy). **No development on the box (D-039)** — M6 deploy files get built on the laptop. Earlier: paused 2026-10-24. Everything committed + pushed (`cd73197`). Milestones 1–5 + 7 (multi-user) + configuration done. Next: **Milestone 6 = v1.0 release** on the Debian box (fresh install) — planned Mon 2026-10-26, user may start it earlier (was cleaning out the box on 2026-10-24). **Read "Resume here" first.** Repo: https://github.com/SSheffer1/ptrack
> **Last updated:** 2026-10-24 (box: Debian trixie, being trimmed)

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
- **Stack (built):** Svelte 5 + TypeScript UI, packaged as an **Android APK via Capacitor**; the phone keeps **its own copy as a change log** (works fully offline, D-032) and syncs with a **Python/FastAPI + SQLite server** (Alembic migrations). Desktop/iPhone use the same UI in a browser, served by the server. Phone reminders are local notifications. Family accounts with shared projects (D-035). Server settings in `server/ptrack.toml`, personal preferences synced (D-038). License GPL-3.0-or-later.
- **Planned (M6):** Docker Compose on the home Debian box, **Caddy (HTTPS)**, nightly backups; v1.0 release.

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
- ~~Q9.~~ Answered 2026-10-25: the name is **PTrack** (D-041).
- ~~Q11.~~ Done 2026-10-24 (D-038). Was: **User wants a single config file** for the choices listed in `CONFIGURATION.md` (e.g. `ptrack.toml` for the server + the in-app Settings page for per-device options) instead of constants spread across code. Keep CONFIGURATION.md updated whenever a setting changes or is added.
- ~~Q12.~~ Answered 2026-10-24: the Debian box will be a **totally fresh install and setup**; start with an empty database. Current data is test data.

---

## Multi-user design (D-035, built 2026-10-24 — kept for reference)

- **Users:** `user` table (id, username, display name, password hash via stdlib `hashlib.scrypt` — no new dependency, is_admin). Accounts created by the admin only (no sign-up). Existing `owner_id = "owner"` data migrates to the admin's account.
- **Login:** each device signs in once and gets its own long-lived token (random; server stores only its hash; revocable per device). Sent as `Authorization: Bearer …` by browser and phone.
- **Membership:** `member` (project_id, user_id, role `owner` | `editor`). Access to items/comments follows their project. Members are synced so the phone can show names offline.
- **Assignee:** `item.assignee_id` (nullable; must be a member of the ticket's project). Filter "assigned to me".
- **Sync:** each change carries its project; a device only receives changes for projects its user is a member of, and the server checks membership on upload. Membership change → server bumps that user's *epoch*; devices that see a new epoch drop their confirmed data, keep unsent edits, and re-download from cursor 0 (simple and always correct at family scale).
- **Ticket numbers:** unchanged, per project, server-assigned.
- **Permissions (user, 2026-10-24):** anyone can create projects and share them (creator = owner). Editors: create, edit, comment on tickets. Owner only: rename/delete project, manage members, and (assumed — editors weren't given it) delete tickets.
- **Notifications (user):** "the assignee decides everything about notifications" → reminders on a ticket are the assignee's (only they're notified, only they can change that ticket's reminders); unassigned → the creator (assumed). Reminder defaults must be end-user configurable (per-user settings, part of the config phase).

---

## Milestone 6 plan: v1.0 release on the Debian box (planned Mon 2026-10-26; may start earlier)

This deploy **is the initial product release** (D-037): clean repo, polished README with real install steps, fresh install on the box (Q12: empty database).

Packages for the box (told the user 2026-10-24): server-only Debian install (no desktop; "SSH server" + "standard system utilities"), then `sudo curl ca-certificates git sqlite3 ufw unattended-upgrades`, and Docker Engine + Compose plugin from Docker's official apt repo. No Python/Node/uv on the host — they live in the images.

Ask the user / have ready before starting:
1. Debian **13 "trixie"** already installed on the AM4 APU box (user trimming packages, 2026-10-24) — check nothing Docker/networking needs was removed (iptables, NIC firmware, network config, ca-certificates, openssh-server). Wired to the router? SSH from the laptop working (username, address)? The box will host other services later.
2. DHCP reservation for the box in the router's app (fixed address) — offer to walk through it.
3. Domain: which DNS provider (Q2g)? Needed for a real HTTPS cert at home via Caddy's DNS-01 challenge (API token, kept out of git).
4. Home-only for now, or reachable from outside (port 443 forward; approval to open a port; then Q2c CGNAT check and Q2f dynamic IP / DDNS)?

Build (new `deploy/` folder + server image):
- **Server image**: Python + uv, `uv sync --frozen`, built web app copied in (`static_dir`), runs `ptrack-serve` with a `ptrack.toml` (host 0.0.0.0, database on a volume); migrations on start; non-root user.
- **Caddy** container: reverse proxy, automatic HTTPS (DNS-01 plugin for the provider), room for other services by subdomain.
- **Backups**: nightly SQLite backup to a volume, keep N days; `[backup]` settings in ptrack.toml + CONFIGURATION.md; document restore.
- **First admin**: `docker compose exec ptrack ptrack-admin create-user <name> --admin`.
- **App**: switch to `https://…`, remove `usesCleartextTraffic` (K8); release-signed APK? (ask); rebuild + install.
- **Docs**: README "Self-hosting" with exact steps; COMMANDS.md Docker equivalents; tag v1.0.0? (ask).
- Verify: phone on Wi-Fi + after reconnect (K11 gone), iPhone browser, backup restore, box reboot brings everything back.

---

## Resume here (2026-10-24)

**State:** all work committed + pushed; working tree clean. Last commits: `cd73197` configuration, `850d4b1` multi-user, `2a159f0` GPL license.

**What exists**
- `server/` — FastAPI + SQLModel + SQLite, Alembic (5 migrations, head `78169c540812`), accounts/sign-in (`auth.py`), sharing + permissions + sync (`sync.py`), preferences (`prefs.py`), settings file (`config.py`, `ptrack.example.toml`), CLIs `ptrack-admin` (accounts, show-config) and `ptrack-serve`. **All commands: `server/COMMANDS.md`.** 89 tests.
- `app/` — Svelte 5 + Vite web app + Capacitor 8 Android project. Online mode (browser) vs offline-first (phone): `lib/runtime.svelte.ts`. Local store/sync: `lib/local/`. 35 unit tests + a two-phone e2e (`sync.e2e.test.ts`, needs a scratch server; recipe in its header and COMMANDS.md).
- `docs/CONFIGURATION.md` — every setting in three layers. This log.

**Dev environment on the laptop (Arch Linux, on home Wi-Fi)**
- Restart if needed: `cd server && uv run fastapi dev src/ptrack/main.py --host 0.0.0.0` (user runs this in their own terminal) and `cd app && npm run dev` (Vite :5173, localhost only). Server on :8000 also serves the built web app (`npm run build`) and `app/dist/ptrack.apk` (copied by hand after each APK build; dist is gitignored).
- Dev DB `server/ptrack.db`: test data, with an admin account (the user) and a family test account.
- Test devices: an Android phone over USB adb (sometimes needs a re-plug or a phone restart) and an iPhone using the web app. Addresses, device ids and account names: laptop-only `CLAUDE.local.md`. ufw on the laptop allows 8000/tcp from the home subnet.
- **K11:** after a phone rejoins Wi-Fi it often can't reach the laptop until the laptop pings it. Goes away with the wired Debian server.
- Build + install APK: `cd app && npm run build && npx cap sync android && (cd android && ./gradlew assembleDebug) && adb install -r android/app/build/outputs/apk/debug/app-debug.apk`.

**Shelved (user decision, may revisit):** kanban board (D-033), quick-add (D-034). **Ideas not started:** app icon, ICS feed for phone calendars, offline desktop app (Tauri), release-signed APK, renaming the project (Q9).

---

## Known Issues / Tech Debt

- K1. Clock skew: LWW trusts device timestamps. A phone with a clock far in the future would win every conflict and push the server clock forward (`sync._observe`). Mitigation idea: reject/clamp ts too far ahead of server time.
- K2. Server clock (`sync._clock`) is in-memory; fine for one process, resets on restart (wall clock covers it).
- ~~K3.~~ Resolved: keys unique server-wide; offline clashes renamed (GYM → GYM2).
- ~~K4. No auth.~~ Resolved 2026-10-24 (M7 step 1): accounts + per-device tokens. Still to consider before internet exposure: login rate limiting beyond the 1 s delay, HTTPS.
- K5. No migrations — `create_all` only. Add Alembic before there's data worth keeping. **Resolved 2026-10-23:** Alembic set up (D-030).
- K6. Moving a ticket between projects isn't supported (would need renumbering).
- K8. `android:usesCleartextTraffic="true"` in AndroidManifest (plain HTTP to the LAN server). Remove when HTTPS via Caddy exists (M6).
- K9. Server on the LAN without HTTPS: passwords and tokens travel unencrypted on the home network. Accepted for LAN testing; fixed by M6. Before internet exposure also consider login rate limiting (only a 1 s delay now).
- K10. Dev laptop's LAN IP is DHCP-assigned; if it changes, the phones' server address breaks. Moot once the server is on the Debian box with a DHCP reservation.
- K11. **Phone can't reach the laptop after rejoining Wi-Fi** ("No route to host") until the laptop pings it. Confirmed by repeat tests 2026-10-24 (Android phone and iPhone). Likely the mesh Wi-Fi (laptop on 6 GHz) not delivering the phone's ARP broadcasts. Not an app bug. Fix: wired Debian server. Stopgap: ping keep-alive.
- K12. Browser "offline-first" test mode: edits made in it stay in that browser if you switch back to online mode before they sync. User declined a warning (dev/test switch).
- ~~K7. Personal email in author fields.~~ Fixed: repo-local git identity and `server/pyproject.toml` use `SSheffer1 <235915830+SSheffer1@users.noreply.github.com>` (GitHub private address, since repo is public). Global git config untouched.

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
| D-018 | 2026-10-21 | Early build/test is LAN-only; public exposure (port 443) later, once opening a port is approved. For HTTPS on LAN, prefer a real cert via Caddy DNS-01 challenge on a subdomain pointing at the server's LAN IP (needs DNS provider API, Q2g); fallback is plain HTTP with Android cleartext allowed for dev builds only. | Port forward pending approval to open a port; LAN-first lets work start now. | Active |
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
| D-033 | 2026-10-24 | Kanban board shelved (not in v1). | User: "idk if i love the feature". Revisit later. | Active |
| D-034 | 2026-10-24 | Quick-add shelved (not in v1). Proposal kept for later: one box, markers `@project #label !priority due:… 10am every:…`, live parse preview, `/` to focus. | User: shelve it; wants to think about multi-user + configuration instead. | Active |
| D-035 | 2026-10-24 | **Multi-user = shared projects (model B).** Projects private by default; owner can add editors. Users = family members only (no public sign-up). Tickets can be assigned to another account (assignee, separate from the assigned date). Configuration redesign (Q11) comes after multi-user. Supersedes "single user" parts of R4/D-014. | User chose B over separate accounts (A) / one shared workspace (C). | Active |
| D-036 | 2026-10-24 | License: **GPL-3.0-or-later** (LICENSE from gnu.org, sha256 3972dc97…; SPDX in pyproject.toml + package.json). All deps MIT/BSD/Apache-2.0 → compatible. | User: "I need to have a gpl license on the github page". | Active |
| D-037 | 2026-10-24 | The Monday server deploy = **initial product release (v1.0)**; GitHub repo must be clean: polished README (project page), dev notes in `docs/` (PROJECT_LOG.md stays public, CONFIGURATION.md), root = README, LICENSE, code folders. No history rewrite, no release tag requested (yet). | User request + choices in AskUserQuestion. | Active |
| D-038 | 2026-10-24 | Configuration in three layers: (1) server settings in `server/ptrack.toml` (`config.py`, stdlib tomllib; sections server/database/accounts/sync; unknown keys = error; env PTRACK_CONFIG/PTRACK_DB/PTRACK_STATIC override; `ptrack-admin show-config`; `ptrack-serve` runs uvicorn from it), (2) per-user preferences synced through the change log as entity `prefs` (id = user id, scope `user:<id>`, only own devices receive them, only owner may write; server validates in `prefs.py`, app holds defaults in `prefs.svelte.ts`): default reminders timed/untimed, untimed hour, week start, soon days, default statuses, default sort, (3) built-in behavior in code (statuses, priorities, roles…). | User: "set the config stuff up however it makes sense, a set of server side configs and some per user configs". | Active |
| D-039 | 2026-10-24 | **No development on the server box.** The laptop is the only dev machine (code, tests, commits, pushes). The box only pulls from GitHub and runs `docker compose`; its clone is pull-only. Deploy files (`deploy/`) are written and tested on the laptop. The box is managed from the laptop over SSH (or by the user running given commands). Supersedes the stick's HANDOFF.md, which told a Claude on the box to build M6 there. | User: "i really dont want any development to happen from the box". | Active |
| D-040 | 2026-10-24 | (1) **The box is a running product in testing**: back up its data before any change, keep downtime minimal. (2) **GitHub must always be sanitized and usable out of the box**: no IPs, device ids, family names, secrets or machine-specific settings in tracked files; a fresh clone + the README's commands must work. Private specifics live in the laptop-only, git-ignored `CLAUDE.local.md`. The log was sanitized accordingly (older commits still contain some details; a history rewrite would need a force-push and the user's OK). | User: "the box is a running product rn in testing and anything on the github should be sanitzied so that at any given moment someone could clone and use it out of the box". | Active |
| D-041 | 2026-10-25 | Product name **PTrack** everywhere a person sees it: header, page title, Android app label, sign-in screen, README, API title. Technical names stay `ptrack` (repo, Python package, `ptrack-admin`/`ptrack-serve`, Docker names, Android app id `io.github.ssheffer1.ptrack`, data file names) — renaming them would break installs and links for no visible gain. | User: "i think im keeping the name PTrack". | Active |
| D-017 | 2026-10-21 | No Tailscale/third-party tunnel unless forced by CGNAT. Use user's own domain + port forward + Caddy. | User objects to extra moving parts and dependencies. | Active |

---

## Event Log

- **2026-10-21** — Project kicked off. User described goal: cross-platform personal issue tracker + calendar. Claude surveyed prior art and tech feasibility (from model knowledge, no live web search yet), drafted three candidate architectures and a data model sketch, and created this log. `ptrack/` was empty.
- **2026-10-21** — User answered Q1/Q2/Q3/Q5/Q6: Android (iOS optional), home server OK (ports uncertain), standalone calendar preferred if good else Google, goal > learning but must understand it, knows Python/C++/HTML/MATLAB with resources for Java/Haskell/Nix. Claude proposed stack D-002..D-008 (PWA + Tailscale) and a v1 scope.
- **2026-10-21** — User: server is Debian on AM4 APU (multi-service), prefers to avoid Tailscale (will open port), wants a real APK with offline use, single-user now / maybe multi-user far future, Google import nice-to-have, dislikes name "ptrack". Claude revised plan: Capacitor APK + local SQLite + hand-rolled sync, Caddy on 443, Docker Compose (D-009..D-015). Superseded D-002/004/005/008. Offline + APK moved into v1 scope; Google import → stretch; iOS → out (needs Mac + Apple dev account).
- **2026-10-21** — User: already owns a domain; Tailscale objection = extra moving parts + dependency (D-017); browser-only desktop OK for v1, real desktop app later (D-016); didn't know what CGNAT means (explained, Q2c still open). User stepped away before reviewing v1 scope (Q7). **Resume here:** get Q2c result + Q7 answer, then start Next Steps #3.
- **2026-10-21** — User: port opening likely fine, pending approval to open a port; first build/test rounds will be LAN-only (D-018). Q2c (CGNAT) deferred until going public. Still waiting on Q7 (scope).
- **2026-10-21** — Walked user through scope item 6 (list + kanban + filters + saved views); user OK with it as proposed. Explained ticket keys (`HOME-12`). Rest of Q7 still open.
- **2026-10-21** — User confirmed project-prefixed ticket keys (D-019) and said the plan sounds good → v1 scope accepted (D-020). Planning phase essentially done; Q2g (DNS provider) and Q9 (name) don't block coding.
- **2026-10-21** — Explained uv; user agreed (D-021). Dev machine has Python 3.14.8, no uv/pip yet — user to run `sudo pacman -S uv`. Ran `git init` (branch `master`), added README.md + .gitignore. Nothing committed yet (commit only when user asks). **Next:** once uv is installed, `uv init` in `server/` and start Milestone 1.
- **2026-10-21** — **Milestone 1 done (uncommitted).** uv 0.13.4 installed. `server/` created (Python 3.14, FastAPI, SQLModel, pytest). Implemented: tables (`models.py`), change log + per-field LWW + server-assigned ticket numbers + simplified HLC (`sync.py`), REST API for projects/tickets/comments/history + `POST /sync` (`api.py`). REST writes go through the same change path as sync (D-022). 21 tests pass; smoke-tested real server with curl. Design deviations from sketch: no separate `Activity` table — history *is* the change log (D-022); event-only fields deferred to Milestone 4; no project PATCH/rename endpoint yet. See *Known Issues*.
- **2026-10-23** — Session resumed after a few days. User installed + logged into `gh` (account SSheffer1, git protocol ssh). Set repo-local identity to SSheffer1 + noreply email, made first commit, created public GitHub repo and pushed (D-024). Push gotcha: the default SSH key belongs to a different GitHub account; fixed repo-locally with `git config core.sshCommand` pointing at the right key (global SSH config untouched; details in the laptop-only CLAUDE.local.md). **Next:** walk user through what Milestone 1 does (they want to look at it), then Milestone 2.
- **2026-10-24** — User approved; committed + pushed configuration (`cd73197`).
- **2026-10-24** — User paused ("might have more to work on later and might advance the deploy"). Refreshed this log: *Resume here*, *Milestone 6 plan*, summary, restored known issues K8–K12 (lost in an earlier edit), Next Steps. Phone ping keep-alive ended (2 h). User is cleaning out the Debian box and asked which packages it needs (answered; listed in the M6 plan).
- **2026-10-24** — User plugged in a USB stick (exFAT; its other contents left untouched) to carry ptrack to the Debian box. Wrote `ptrack-setup/` on it: `ptrack.bundle` (git bundle of all refs, HEAD `39be13a`; test-clone OK), `ptrack-code/` (git archive of HEAD), `install.sh` (Debian trixie host prep: base packages, Docker official repo + compose plugin, docker group, SSH, ufw allow 22/80/443 + enable, unattended-upgrades, clone bundle → ~/ptrack with origin = GitHub, copy HANDOFF.md → CLAUDE.local.md; idempotent; `bash -n` OK, not run yet), `HANDOFF.md` (context for a separate Claude Code session on the box: project, state, M6 tasks, questions to ask, network facts, user preferences, commit identity, log-conflict warning), `README.txt`, `SHA256SUMS`. Repo: `.gitignore` now ignores `CLAUDE.local.md` (`39be13a`, pushed).
- **2026-10-24 (evening)** — User set up the Debian box early. Found it on the home network (`SSH-2.0-OpenSSH_10.0p2 Debian-7+deb13u4`). No commits pushed from it. User: no development on the box (D-039) → the stick's HANDOFF.md / CLAUDE.local.md instructions are outdated; asked user about install.sh status, a Claude session on the box, wiring + DHCP reservation, and SSH access for managing it from the laptop.
- **2026-10-24 (evening)** — SSH to the box working via a dedicated passphrase-less key and an SSH alias `ptrack-box` (the user's main key has a passphrase and there's no agent, so Claude couldn't use it). Box: Ryzen 3 2200G, 4 cores, 14 GB, 181 GB free; wired (default route) plus a USB Wi-Fi adapter; Docker 29.9.2, Compose v5.6.1; ssh/ufw/unattended-upgrades active; repo at `1f7d834`, push URL not yet disabled; CLAUDE.local.md present. **Found: a Claude session on the box (2 `claude` processes, ~5 h old) had already built a first deploy before D-039** — untracked `deploy/{Dockerfile,compose.yaml,Caddyfile,ptrack.toml}` + `.dockerignore`; containers `deploy-ptrack-1` (healthy) and `deploy-caddy-1` (plain HTTP on :80, no HTTPS, no backups); volumes `deploy_ptrack-data`, `deploy_caddy-data`. Its files look sound (3-stage image: node build → uv venv → python slim, non-root, healthcheck; only Caddy publishes ports). Note `deploy/ptrack.toml` is caught by the `ptrack.toml` gitignore rule. Asked the user how to handle it (recommend: bring the files to the laptop, review/test/commit here, then the box pulls).
- **2026-10-24 (night)** — User stopped the box's Claude session (one `claude` process still listed) and OK'd the plan; reminded: box = running product in testing, GitHub must be sanitized and usable out of the box (D-040). Did: backup of the box DB (sqlite backup API; 2 users, 2 projects, 1 ticket) into the volume and `~/ptrack-backups/` on the box; copied the box session's `deploy/` files + `.dockerignore` to the laptop (unchanged — they're what the box is already running, so the build is proven; the laptop has no Docker); `.gitignore` rule narrowed to `/server/ptrack.toml` so `deploy/ptrack.toml` is tracked; sanitized the public log (addresses, device ids, account names, personal circumstances → laptop-only `CLAUDE.local.md`; scan of tracked files clean); README: Self-hosting section, features updated, `deploy/` in layout; COMMANDS.md: Docker section.
- **2026-10-24 (night)** — Committed + pushed `95f567c` (deploy/ + sanitized docs). Box: verified its untracked deploy files were byte-identical to the pushed ones (sha256), removed them and the outdated `CLAUDE.local.md`, `git pull --ff-only` → `95f567c`, push URL set to `DISABLED`, working tree clean. Fresh backup, then `docker compose -f deploy/compose.yaml build` + `up -d`: ptrack container recreated, healthy within ~30 s, Caddy untouched; accounts, projects and tickets intact. Box now runs exactly what's on GitHub. Still open: one `claude` process on the box; HTTPS; backups automation; DHCP reservation.
- **2026-10-24 (night)** — User: sanitize GitHub, no personal information (D-040). Scanned all history; rewrote every commit with `git filter-branch --tree-filter` and a local replacement script (`git-filter-repo` download was blocked as outside code): home-network addresses, a device serial, account and personal names, machine/key names, USB stick details and personal circumstances replaced with neutral text; generic examples kept. Verified: 0 matches left in any commit, newest tree identical to before (`b075bd1`), messages/authors unchanged. Force-pushed with a lease (`95f567c` → `e013db9`; the first attempt was blocked by the safety check, then done at the user's explicit request); laptop and box reset to the new history (both had no local changes; box push still disabled; no rebuild needed). Fresh clone from GitHub re-scanned: clean. Caveats: GitHub may serve old commits by direct SHA until its garbage collection (GitHub Support can purge); the USB stick's bundle still holds the old history (user's private stick).
- **2026-10-25** — User: focus on app development. Background sync slowed from every 30 s to every 5 min (`SYNC_EVERY_MS`); syncing 1 s after an edit and on app resume kept. Top bar: **Sync now** button (`refreshNow()`: sync in offline-first mode, re-fetch in online mode; spinning ↻ while syncing) and **Settings** button, next to the sync badge (on narrow screens only its colored dot). CONFIGURATION.md updated. Type check + 35 app tests pass; APK built (phone not connected for install). Uncommitted.
- **2026-10-25** — User: sync frequency should be configurable → new personal preference `sync_minutes` (1/5/15/30/60, 0 = never; default 5; server range 0–1440; runtime re-arms the timer via `$effect.root` when it changes). Server 89 + app 35 tests pass. APK installed on the user's phone (it syncs with the server box, signed in). **Deploy order matters:** the box's server must be updated before anyone sets `sync_minutes`, or it rejects the sync batch (unknown preference). Uncommitted.
- **2026-10-25** — Committed + pushed `959dd03` (scan clean). Box: backup, `git pull`, rebuild, `up -d`: ptrack recreated and healthy in ~30 s, data intact, server accepts `sync_minutes`. The preference is now safe to use on the phone.
- **2026-10-25** — User (picky about looks): header was wrapping into two uneven rows. Now two fixed rows: **ribbon** (name left; sync dot/status, Sync now, Settings right; never wraps) and **tabs** (List/Calendar/Agenda/Projects with an underline on the active one; scrolls sideways instead of wrapping). Checked on the phone with `adb exec-out screencap` (Claude can view screenshots) — renders as intended. Installed on the phone; uncommitted. Noticed: the List toolbar below still wraps into three rows on a phone.
- **2026-10-25** — Settings button is now a large gear only (`aria-label`/title "Settings"; U+FE0E keeps it a plain glyph, not an emoji), same height as Sync now. Verified by phone screenshot. User likes the sync button as is. Uncommitted.
- **2026-10-25** — Name **PTrack** (D-041; Q9 closed): header, page title, Android label (strings.xml + capacitor.config appName), sign-in screen, README, API title; technical names unchanged. Filters toolbar (`Filters.svelte`) restructured into two rows on phones — search + project picker, then the view's controls (List: sort left, +Project/+Ticket right; Calendar: ‹ Today › right) — side by side from 760 px. Verified by phone screenshot. Uncommitted.
- **2026-10-25** — App icon. Explored options on a private Design canvas (artifact, not in the repo); user chose a **P-trap** (tailpiece up to the sink, J-bend, trap arm to the wall, two slip-nut collars) with a tiny **mouse in the loop** (not touching the pipe), white on #3b5bdb. Implemented: `app/icon/` SVG sources (square, rounded, round, favicon) + `build.sh` (resvg) rendering legacy launcher PNGs (all densities), launch-screen PNGs, `app/public/apple-touch-icon.png` and `favicon.svg`; Android adaptive icon as a vector drawable (`drawable/ic_launcher_foreground.xml`, 3x scale into the 72 dp safe area) with `<monochrome>` for themed icons; `ic_launcher_background` = #3B5BDB; launch theme uses the icon on blue (Android 12+ splash API attrs). Removed Capacitor's template foreground PNGs and background drawable; `index.html` links favicon + apple-touch-icon + theme-color. Installed on the phone. Uncommitted (with the header/filters/name changes).
- **2026-10-25** — User: the installed icon "doesn't work" (details asked: old logo cached vs. blank) and wants a redesign: thicker pipe, a break in it, a mouse head poking out of the hole. Drew it side-on (a face-on round head with two round ears resembles a famous trademarked mouse). Iterated locally with resvg renders (first tries blended head into pipe); current: pipe stroke 4, break at the bottom-right of the J-bend, head with a thin background-blue outline, round ear, eye, nose dot. On the design canvas for review; not yet in `app/icon/`.
- **2026-10-25** — Icon round 2: user wants the pipe intact (sides intact), a black hole in it, and a **face-on** mouse head poking out toward the viewer. Drawn with a pointed, rodent-like face (not three circles, to avoid a trademarked look): intact P-trap (stroke 4.6, two collars), dark (#111114) elliptical hole on the front of the bend, mouse face with ears, eyes, pink inner ears and nose, whiskers; scaled 1.2x. Small sizes drop pink/whiskers; 18 px = pipe + hole. On the design canvas for review.
- **2026-10-25** — User chose the jagged-hole design (hole moved along the bend to the right). **Bug found:** the first icon showed Android's default robot head on blue because Capacitor's template has `res/drawable-v24/ic_launcher_foreground.xml`, which wins over `res/drawable/` on Android 7+. Deleted it. New icon written everywhere: `app/icon/*.svg` (jagged hole path generated once, 16 alternating points), vector foreground (mouse group: pivot 12,18.5, scale 1.2, translate 2.54,-0.56; ears as rotated groups), new pipe-only `drawable/ic_launcher_monochrome.xml` for themed icons (one tint would merge mouse and hole), favicon = pipe + hole; PNGs re-rendered. Gotchas: Gradle kept the deleted resource in its merge cache → "resource not found" until `./gradlew clean`; and my build+install command used `;`, so the failed build reinstalled the previous APK — always chain install with `&&` after a successful build. Verified the APK no longer contains the drawable-v24 foreground; installed on the phone.

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
9. ~~Milestone 7: multi-user (accounts, shared projects, assignees).~~ Done 2026-10-24.
10. ~~Configuration: server ptrack.toml + per-user preferences + COMMANDS.md.~~ Done 2026-10-24.
11. **Milestone 6 = v1.0 release** on the Debian box: see *Milestone 6 plan*.
12. Later / optional: app icon, ICS feed, kanban (shelved), quick-add (shelved), offline desktop app, project name (Q9).
