"""Per-person preferences, set in the app and synced to all of that person's devices.

They travel through the change log like tickets ("set week_start to monday"),
as entity "prefs" whose id is the user's id. Only the user can change theirs,
and only their devices receive them (scope "user:<id>", see sync.py).

The server only checks and stores them; the app applies them and holds the
defaults (app/src/lib/prefs.svelte.ts). An unset preference means the default.
"""

from typing import Any, Literal

from pydantic import Field, TypeAdapter

from .models import SortOrder, Status
from .reminders import normalize_reminders

Hour = Field(ge=0, le=23)

# Name → type. Keep in step with app/src/lib/prefs.svelte.ts.
PREFS: dict[str, Any] = {
    "reminders": list[str],  # default reminders for tickets with a due date, e.g. ["0"]
    # Replaced by "reminders" (one default for all tickets). Still accepted so an
    # app that hasn't been updated yet can sync; the app no longer reads them.
    "reminders_timed": list[str],
    "reminders_untimed": list[str],
    "untimed_hour": int,  # the hour (0–23) an untimed ticket counts as due; reminders count from it
    "week_start": Literal["sunday", "monday"],
    "soon_days": int,  # due dates turn orange this many days ahead (0–14)
    "default_statuses": list[Status],  # statuses shown when the app opens
    "default_sort": SortOrder,
    "sync_minutes": int,  # background sync interval on offline-first devices; 0 = never (0–1440)
}

RANGES = {"untimed_hour": (0, 23), "soon_days": (0, 14), "sync_minutes": (0, 1440)}


def scope(user_id: str) -> str:
    return f"user:{user_id}"


def validate(name: str, value: Any) -> Any:
    """Return the cleaned value, or raise ValueError."""
    if name not in PREFS:
        raise ValueError(f"unknown preference {name!r}")
    if value is None:
        return None  # back to the default
    value = TypeAdapter(PREFS[name]).validate_python(value)
    if name in RANGES:
        low, high = RANGES[name]
        if not low <= value <= high:
            raise ValueError(f"{name} must be between {low} and {high}")
    if name.startswith("reminders"):
        value = normalize_reminders(value, allow_specific_times=False)
    return value
