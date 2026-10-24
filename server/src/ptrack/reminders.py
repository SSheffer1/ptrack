"""Reminder offsets.

A ticket's `reminders` is a list of offsets from its due moment: "0" (at the
due moment), "-30m", "-8h", "-2d". The due moment is the due date at its due
time, or at 9:00 if it has no time. The phone schedules the notifications
itself (app/src/lib/local/reminders.ts); the server only checks and stores them.

None means the default: 8 hours before a timed ticket, 9:00 on the day for an
untimed one. An empty list means no reminders.
"""

import re

OFFSET_RE = re.compile(r"^(0|-\d{1,4}[mhd])$")


def normalize_reminders(reminders: list[str] | None) -> list[str] | None:
    """Check offsets and return them cleaned up and sorted (earliest first), or raise ValueError."""
    if reminders is None:
        return None
    cleaned = {r.strip().lower() for r in reminders}
    for r in cleaned:
        if not OFFSET_RE.match(r):
            raise ValueError(f"invalid reminder {r!r}; use e.g. '0', '-30m', '-8h', '-1d'")
    return sorted(cleaned, key=_minutes)


def _minutes(offset: str) -> int:
    if offset == "0":
        return 0
    return int(offset[:-1]) * {"m": 1, "h": 60, "d": 1440}[offset[-1]]
