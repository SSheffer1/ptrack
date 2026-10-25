import sqlite3
from contextlib import closing
from datetime import datetime, timedelta

from ptrack import backup
from ptrack.config import ConfigError, load

import pytest


def make_db(path):
    with closing(sqlite3.connect(path)) as db:
        db.execute("create table t (x)")
        db.execute("insert into t values (42)")
        db.commit()
    return path


def test_backup_copies_the_database(tmp_path):
    db = make_db(tmp_path / "ptrack.db")
    copy = backup.make_backup(db, tmp_path / "backups", datetime(2026, 10, 25, 3, 0))
    assert copy.name == "ptrack-20261025-030000.db"
    with closing(sqlite3.connect(copy)) as c:
        assert c.execute("select x from t").fetchone() == (42,)
    assert not list((tmp_path / "backups").glob("*.partial"))


def test_prune_keeps_recent_and_always_the_newest(tmp_path):
    db = make_db(tmp_path / "ptrack.db")
    folder = tmp_path / "backups"
    now = datetime(2026, 10, 25, 3, 0)
    for days_ago in [30, 20, 10, 1, 0]:
        backup.make_backup(db, folder, now - timedelta(days=days_ago))
    (folder / "notes.txt").write_text("not a backup")
    removed = backup.prune(folder, keep_days=14, now=now)
    assert sorted(p.name for p in removed) == ["ptrack-20260925-030000.db", "ptrack-20261005-030000.db"]
    assert len(backup.list_backups(folder)) == 3
    assert (folder / "notes.txt").exists()

    # Everything expired (server off for a month): the newest stays.
    assert backup.prune(folder, keep_days=1, now=now + timedelta(days=60))
    assert [p.name for _, p in backup.list_backups(folder)] == ["ptrack-20261025-030000.db"]


def test_seconds_until_next_run():
    assert backup.seconds_until(3, datetime(2026, 10, 25, 1, 30)) == 90 * 60
    assert backup.seconds_until(3, datetime(2026, 10, 25, 3, 0)) == 24 * 3600  # just ran: tomorrow
    assert backup.seconds_until(3, datetime(2026, 10, 25, 23, 0)) == 4 * 3600


def test_database_path():
    assert str(backup.database_path("sqlite:////data/ptrack.db")) == "/data/ptrack.db"
    assert str(backup.database_path("sqlite:///ptrack.db")) == "ptrack.db"
    assert backup.database_path("postgresql://x/y") is None


def test_backup_settings(tmp_path):
    path = tmp_path / "ptrack.toml"
    path.write_text("[backup]\nenabled = false\nhour = 4\nkeep_days = 30\ndir = \"/srv/backups\"\n")
    s = load(path, env={})
    assert (s.backup_enabled, s.backup_hour, s.backup_keep_days, s.backup_dir) == (False, 4, 30, "/srv/backups")
    for bad in ["[backup]\nhour = 24\n", "[backup]\nkeep_days = 0\n", "[backup]\nenabled = 1\n", "[backup]\nhour = true\n"]:
        path.write_text(bad)
        with pytest.raises(ConfigError):
            load(path, env={})
