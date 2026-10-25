# PTrack to-do

Everything we've considered, and where it stands. The reasons and details behind
each decision (the `D-###` numbers) are in [docs/PROJECT_LOG.md](docs/PROJECT_LOG.md).

## Next up

- **Fixed address for the server.** Reserve its address in the router's DHCP
  settings so phones don't lose the server if the router hands out a new one.

## v1.0 release

- **Release-signed APK.** The current debug build only installs over adb or from
  the server's `/ptrack.apk`.
- **GitHub Release.** Tag `v1.0.0` with the signed APK attached. It then replaces
  copying the APK to the server by hand (D-047).
- Release checks: phone on Wi-Fi and after reconnecting, iPhone in the browser,
  restoring a backup, server reboot brings everything back.
- HTTPS isn't required for v1.0, which can ship as "for your home network".

## Planned later

- **Calendar feed (ICS).** Lets phone and desktop calendar apps show PTrack due dates.
- **One-time Google Calendar import** of existing events (from a Google Takeout `.ics`).
- **Export your data** in a standard format (requirement R11; nothing exists yet).
- **Move a ticket to another project.** Needs renumbering (K6).
- **Offline desktop app**, probably Tauri around the same UI (D-016). The desktop
  uses the browser for now, online only.
- **Command-line / terminal interface.** List, add and update tickets from a terminal,
  using the server's existing API.
- **MCP server (AI access).** Lets an AI assistant such as Claude read and manage
  tickets through the Model Context Protocol, built on the server's existing API.

## Shelved (may come back)

- **HTTPS.** Plan recorded: move the domain's DNS to deSEC, Caddy gets certificates by
  DNS challenge, no ports opened, then drop plain HTTP from the Android app (D-043, K8, K9).
- **Reaching it from outside the home.** Needs HTTPS first, then a port forward, plus a
  check for CGNAT and a dynamic home IP (Q2c, Q2f). Also stronger login rate limiting
  (K4).
- **iOS app.** Needs a Mac, Xcode, Apple's $99/year program and HTTPS. A cheaper route
  is an installable web app (PWA) (D-042).
- **Kanban board** (D-033).
- **Quick-add box**, e.g. `fix bike !high #home due:fri` (D-034).
- **Off-server backup copies.** Nightly backups stay on the same disk for now (D-044).

## Decided against

- Markdown in descriptions and comments: plain text only (D-045).
- Calendar events with start and end times, and class schedules: the calendar is a view
  of tickets' due dates (D-026).
- Tailscale or other third-party tunnels (D-017).

## Ideas from the original sketch, never picked up

- Subtasks (parent/child tickets) and links between tickets.
- Time estimates and time tracking.
- Attachments.
- Two-way Google Calendar sync.

## Known issues worth fixing

- **Device clock skew (K1).** A phone whose clock runs far ahead wins every sync
  conflict. Fix: reject or clamp timestamps too far past the server's time.
- **Login rate limiting (K4).** Only a 1-second delay after a wrong password today.
  It matters once the server is reachable from outside.

## Done

Tickets with project keys, statuses, priorities, labels, descriptions, comments
(editable and deletable) and full history. Due dates with optional times, plus assigned
and completed dates. Repeating tickets. List, calendar and agenda views with a Status
filter. An offline Android app with sync and reminders, presets and specific times
(D-046). Family accounts, shared projects and assignees. Server settings and synced
personal preferences. Docker deploy with nightly backups. The server serves the APK.
App icon, the PTrack name and a GPL license.
