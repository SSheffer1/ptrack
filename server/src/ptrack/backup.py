"""Nightly database backups.

The server copies its SQLite database once a day (at [backup] hour, server
local time) into a folder of dated files, `ptrack-YYYYMMDD-HHMMSS.db`, and
deletes copies older than [backup] keep_days (never the newest). If the server
starts and the newest copy is over a day old, it makes one straight away, so a
box that was off at 3 AM still gets its backup.

Copies use SQLite's online backup API: safe while the server is running, and
each copy is checked (`PRAGMA quick_check`) before it's kept.

Restoring: see server/COMMANDS.md.
"""

import asyncio
import logging
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path

from .config import settings

log = logging.getLogger("ptrack.backup")

PREFIX, SUFFIX, STAMP = "ptrack-", ".db", "%Y%m%d-%H%M%S"


def database_path(url: str | None = None) -> Path | None:
    """The database file, or None if the database isn't SQLite."""
    url = url or settings.database_url
    return Path(url.removeprefix("sqlite:///")) if url.startswith("sqlite:///") else None


def backup_folder(db: Path) -> Path:
    return Path(settings.backup_dir) if settings.backup_dir else db.parent / "backups"


def list_backups(folder: Path) -> list[tuple[datetime, Path]]:
    """Backups in `folder`, oldest first."""
    found = []
    for path in folder.glob(f"{PREFIX}*{SUFFIX}"):
        try:
            found.append((datetime.strptime(path.name[len(PREFIX) : -len(SUFFIX)], STAMP), path))
        except ValueError:
            continue  # not one of ours
    return sorted(found)


def make_backup(db: Path, folder: Path, now: datetime | None = None) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / f"{PREFIX}{(now or datetime.now()):{STAMP}}{SUFFIX}"
    partial = target.with_name(target.name + ".partial")
    with closing(sqlite3.connect(db)) as source, closing(sqlite3.connect(partial)) as copy:
        source.backup(copy)
        result = copy.execute("PRAGMA quick_check").fetchone()[0]
    if result != "ok":
        partial.unlink(missing_ok=True)
        raise RuntimeError(f"backup failed its check: {result}")
    partial.rename(target)
    return target


def prune(folder: Path, keep_days: int, now: datetime | None = None) -> list[Path]:
    """Delete backups older than `keep_days`, always keeping the newest. Returns what was deleted."""
    backups = list_backups(folder)
    cutoff = (now or datetime.now()) - timedelta(days=keep_days)
    old = [path for when, path in backups[:-1] if when < cutoff]
    for path in old:
        path.unlink()
    return old


def seconds_until(hour: int, now: datetime) -> float:
    """Seconds from `now` to the next `hour`:00."""
    target = now.replace(hour=hour, minute=0, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return (target - now).total_seconds()


def backup_now(now: datetime | None = None) -> Path:
    """Make a backup and prune old ones (used by the nightly task and `ptrack-admin backup`)."""
    db = database_path()
    if db is None:
        raise RuntimeError("backups only work with a SQLite database")
    folder = backup_folder(db)
    path = make_backup(db, folder, now)
    for removed in prune(folder, settings.backup_keep_days, now):
        log.info("deleted old backup %s", removed.name)
    return path


async def run_nightly() -> None:
    """Started with the server; runs until it stops."""
    db = database_path()
    if not settings.backup_enabled or db is None:
        return
    backups = list_backups(backup_folder(db))
    if not backups or datetime.now() - backups[-1][0] > timedelta(days=1):
        await _backup()
    while True:
        await asyncio.sleep(seconds_until(settings.backup_hour, datetime.now()))
        await _backup()


async def _backup() -> None:
    try:
        path = await asyncio.to_thread(backup_now)
        log.info("backup written: %s", path)
    except Exception:
        log.exception("backup failed")
