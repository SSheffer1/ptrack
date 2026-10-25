"""Server settings, read once at startup from a TOML file.

The file is `ptrack.toml` in the directory the server runs from, or the path in
the PTRACK_CONFIG environment variable. Every setting has a default, so the file
is optional; see ptrack.example.toml for all of them. A misspelled setting is an
error rather than being silently ignored.

Two environment variables override the file (handy for Docker and tests):
PTRACK_DB (database.url) and PTRACK_STATIC (server.static_dir).

Per-person preferences (reminder defaults etc.) are not here; they're synced
like tickets and set in the app (see prefs.py).
"""

import os
import tomllib
from dataclasses import asdict, dataclass, fields
from pathlib import Path

# ptrack/app/dist next to the server/ directory, when running from a checkout.
DEFAULT_STATIC = str(Path(__file__).parents[3] / "app" / "dist")


@dataclass(frozen=True)
class Settings:
    # [server]
    host: str = "127.0.0.1"  # "0.0.0.0" = reachable from other devices on the network
    port: int = 8000
    static_dir: str = DEFAULT_STATIC  # the built web app to serve at /; ignored if missing
    # [database]
    database_url: str = "sqlite:///ptrack.db"
    # [accounts]
    min_password_length: int = 8
    login_delay_seconds: float = 1.0  # wait after a wrong password, to slow down guessing
    device_idle_days: int = 0  # sign a device out after this many days unused; 0 = never
    # [sync]
    sync_page_size: int = 1000  # changes per sync response
    # [backup]
    backup_enabled: bool = True  # nightly copies of the database (SQLite only)
    backup_dir: str = ""  # where they go; "" = a "backups" folder next to the database
    backup_hour: int = 3  # hour of the day (0-23, server's local time)
    backup_keep_days: int = 14  # older copies are deleted; the newest is always kept


# Where each setting lives in the file: section → {key in file: Settings field}.
SECTIONS: dict[str, dict[str, str]] = {
    "server": {"host": "host", "port": "port", "static_dir": "static_dir"},
    "database": {"url": "database_url"},
    "accounts": {
        "min_password_length": "min_password_length",
        "login_delay_seconds": "login_delay_seconds",
        "device_idle_days": "device_idle_days",
    },
    "sync": {"page_size": "sync_page_size"},
    "backup": {
        "enabled": "backup_enabled",
        "dir": "backup_dir",
        "hour": "backup_hour",
        "keep_days": "backup_keep_days",
    },
}

ENV_OVERRIDES = {"PTRACK_DB": "database_url", "PTRACK_STATIC": "static_dir"}


class ConfigError(ValueError):
    pass


def load(path: Path | None = None, env: dict[str, str] | None = None) -> Settings:
    env = dict(os.environ) if env is None else env
    path = path or Path(env.get("PTRACK_CONFIG", "ptrack.toml"))
    values: dict[str, object] = {}
    if path.exists():
        try:
            data = tomllib.loads(path.read_text())
        except tomllib.TOMLDecodeError as e:
            raise ConfigError(f"{path}: {e}") from e
        for section, table in data.items():
            if section not in SECTIONS or not isinstance(table, dict):
                raise ConfigError(f"{path}: unknown section [{section}]")
            for key, value in table.items():
                if key not in SECTIONS[section]:
                    raise ConfigError(f"{path}: unknown setting {section}.{key}")
                values[SECTIONS[section][key]] = value
    for var, name in ENV_OVERRIDES.items():
        if env.get(var):
            values[name] = env[var]

    types = {f.name: f.type for f in fields(Settings)}
    for name, value in values.items():
        expected = types[name]
        if expected is bool:
            ok = isinstance(value, bool)
        else:  # TOML true/false must not count as a number
            ok = isinstance(value, (int, float) if expected is float else expected) and not isinstance(value, bool)  # type: ignore[arg-type]
        if not ok:
            raise ConfigError(f"setting {name} should be a {getattr(expected, '__name__', expected)}, not {value!r}")
    settings = Settings(**values)  # type: ignore[arg-type]
    if settings.min_password_length < 1 or settings.device_idle_days < 0 or settings.sync_page_size < 1:
        raise ConfigError("min_password_length and sync_page_size must be positive; device_idle_days ≥ 0")
    if not 0 <= settings.backup_hour <= 23 or settings.backup_keep_days < 1:
        raise ConfigError("backup hour must be 0-23 and keep_days at least 1")
    return settings


def describe(settings: Settings) -> str:
    """The effective settings, in the file's layout (for `ptrack-admin show-config`)."""
    current = asdict(settings)
    lines = []
    for section, keys in SECTIONS.items():
        lines.append(f"[{section}]")
        lines += [f"{key} = {_toml(current[name])}" for key, name in keys.items()]
        lines.append("")
    return "\n".join(lines)


def _toml(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return repr(value).replace("'", '"')


settings = load()
