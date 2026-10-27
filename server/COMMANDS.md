# Server commands

Run these from the `server/` folder. `uv run` uses the project's own Python
environment, so there's nothing to activate first.

## Accounts

| Command | What it does |
|---|---|
| `uv run ptrack-admin create-user <name> --name "Display Name"` | Add an account. Asks for the password. |
| `uv run ptrack-admin create-user <name> --admin` | Add an admin (can manage accounts in the app's Settings). |
| `uv run ptrack-admin set-password <name>` | Set or reset someone's password. Asks for it twice. |
| `uv run ptrack-admin rename-user <old> <new>` | Change a username (what you type to sign in). |
| `uv run ptrack-admin list-users` | Show every account, with admin / disabled / no-password flags. |
| `uv run ptrack-admin disable-user <name>` | Block sign-in and sign them out everywhere (data is kept). |
| `uv run ptrack-admin enable-user <name>` | Undo `disable-user`. |
| `uv run ptrack-admin set-admin <name>` | Make an account an admin (`--off` to remove it). |
| `uv run ptrack-admin sign-out <name>` | Sign an account out on all its devices (e.g. lost phone). |
| `uv run ptrack-admin set-role <PROJECT> <name> owner` | Make someone an owner (or `editor`) of a project, adding them if needed. A project can have several owners; the last one can't be demoted. |

Usernames are lowercase letters, digits and `. _ -`, 2–32 characters, starting
with a letter. Admins can also do most of this in the app: Settings → Family accounts.

## Running the server

| Command | What it does |
|---|---|
| `uv run ptrack-serve` | Run the server using `ptrack.toml` (host, port, database…). For real use. |
| `uv run fastapi dev src/ptrack/main.py` | Development server on :8000 that restarts on every code change. |
| `uv run fastapi dev src/ptrack/main.py --host 0.0.0.0` | Same, reachable from phones on the network. |
| `uv run ptrack-admin show-config` | Print the settings in effect (`ptrack.toml` + defaults). |
| `uv run ptrack-admin backup` | Back up the database now (and delete expired backups). |
| `uv run ptrack-admin list-backups` | Show the backups, newest last. |

Settings: copy `ptrack.example.toml` to `ptrack.toml` and edit it. Every setting is
explained in that file. `PTRACK_CONFIG=/path/to/file.toml` uses a different file;
`PTRACK_DB` overrides the database.

Interactive API docs: http://localhost:8000/docs (sign in with the **Authorize**
button by pasting a token, or use the app).

## Database

| Command | What it does |
|---|---|
| (nothing) | The server upgrades the database automatically on startup. |
| `uv run alembic current` | Show which schema version the database is at. |
| (nothing) | The server also backs itself up every night at 3 AM into `backups/`, keeping 14 days ([backup] in `ptrack.toml`). |

After changing `src/ptrack/models.py`, generate a migration (stop the dev server
first: its auto-reload would apply a half-written one):

```bash
PTRACK_DB=sqlite:////tmp/scratch.db uv run alembic upgrade head
PTRACK_DB=sqlite:////tmp/scratch.db uv run alembic revision --autogenerate -m "what changed"
```

Then read the generated file in `src/ptrack/migrations/versions/` and run the tests.

## Tests

| Command | What it does |
|---|---|
| `uv run pytest` | All server tests (includes a check that migrations match the models). |
| `uv run pytest tests/test_sharing.py -v` | One file, listing each test. |

The app's end-to-end test drives two "phones" against a real server; see the
comment at the top of `app/src/lib/local/sync.e2e.test.ts`.

## Docker (home server)

From the repo root, on the server. `C="docker compose -f deploy/compose.yaml"` saves typing.

| Command | What it does |
|---|---|
| `$C up -d --build` | Build and start (or update after `git pull`). Data is kept. |
| `$C ps` | Is it running and healthy? |
| `$C logs -f ptrack` | Server log (Ctrl+C to stop following). |
| `$C exec ptrack ptrack-admin <command>` | Any `ptrack-admin` command above, inside the container. |
| `$C restart ptrack` | Restart the server. |
| `$C down` | Stop everything (data stays in the `deploy_ptrack-data` volume). |
| `$C exec ptrack ptrack-admin list-backups` | The nightly backups (in the data volume, `/data/backups`). |
| `$C exec ptrack ptrack-admin backup` | Back up now. |
| `docker cp deploy-ptrack-1:/data/backups ./ptrack-backups` | Copy the backups out of Docker, e.g. to keep another copy elsewhere. |

### Restoring a backup

The backups sit on the same disk as the database: they protect against mistakes and
corruption, not a dead disk. Copy them elsewhere now and then (command above).

```bash
$C exec ptrack ptrack-admin list-backups               # pick one, e.g. ptrack-20261025-030000.db
$C exec ptrack ptrack-admin backup                     # first, a copy of how things are now
$C stop ptrack
docker run --rm -v deploy_ptrack-data:/data --entrypoint cp ptrack \
  /data/backups/ptrack-20261025-030000.db /data/ptrack.db   # uses the PTrack image itself
$C start ptrack
```

Devices sync to the restored state on their next sync; edits made after the backup are lost.
