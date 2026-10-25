"""Reminders.

A ticket's `reminders` is a list of two kinds of entries:
- offsets from its due moment: "0" (at the due moment), "-30m", "-8h", "-2d".
  The due moment is the due date at its due time, or at 9:00 if it has no time.
- specific times, in local time: "@2026-10-27T19:30". These work without a
  due date too.

The phone schedules the notifications itself (app/src/lib/reminders.ts); the
server only checks and stores them, and moves specific times along when a
recurring ticket's next copy is made.

None means the default: 8 hours before a timed ticket, 9:00 on the day for an
untimed one. An empty list means no reminders.
"""

import re
from datetime import datetime, timedelta

OFFSET_RE = re.compile(r"^(0|-\d{1,4}[mhd])$")
AT_RE = re.compile(r"^@\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$")
AT_FORMAT = "@%Y-%m-%dT%H:%M"


def normalize_reminders(reminders: list[str] | None, allow_specific_times: bool = True) -> list[str] | None:
    """Check reminders and return them cleaned up and sorted (offsets earliest first, then
    specific times in order), or raise ValueError."""
    if reminders is None:
        return None
    cleaned = {_clean(r) for r in reminders}
    for r in cleaned:
        if AT_RE.match(r):
            if not allow_specific_times:
                raise ValueError("default reminders can't be specific times")
            datetime.strptime(r, AT_FORMAT)  # a real date and time, or ValueError
        elif not OFFSET_RE.match(r):
            raise ValueError(f"invalid reminder {r!r}; use e.g. '-8h', '-1d', '0' or '@2026-10-27T19:30'")
    return sorted(cleaned, key=_sort_key)


def shift_reminders(reminders: list[str] | None, days: int) -> list[str] | None:
    """Move specific-time reminders by `days` (for a recurring ticket's next copy)."""
    if reminders is None or days == 0:
        return reminders
    shifted = [
        (datetime.strptime(r, AT_FORMAT) + timedelta(days=days)).strftime(AT_FORMAT) if AT_RE.match(r) else r
        for r in reminders
    ]
    return normalize_reminders(shifted)


def _clean(r: str) -> str:
    r = r.strip()
    return r.upper() if r.startswith("@") else r.lower()


def _sort_key(r: str) -> tuple[int, int, str]:
    if r.startswith("@"):
        return (1, 0, r)
    if r == "0":
        return (0, 0, "")
    return (0, int(r[:-1]) * {"m": 1, "h": 60, "d": 1440}[r[-1]], "")
