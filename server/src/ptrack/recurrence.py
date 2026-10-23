"""Recurring tickets.

A ticket's `repeat` field holds a recurrence rule in the iCalendar RRULE format
(RFC 5545), the same format Google Calendar and phone calendars use:

    FREQ=WEEKLY;BYDAY=FR             every Friday
    FREQ=WEEKLY;INTERVAL=2           every 2 weeks
    FREQ=MONTHLY;BYMONTHDAY=1        the 1st of every month
    FREQ=WEEKLY;UNTIL=20261211       weekly until Dec 11

When a recurring ticket is marked done, the server creates the next copy with
the next due date (see sync._spawn_next_occurrences).
"""

from datetime import date, datetime, time

from dateutil.rrule import rrule, rrulestr


def _parse(rule: str, start: date) -> rrule:
    parsed = rrulestr(rule, dtstart=datetime.combine(start, time()))
    assert isinstance(parsed, rrule)
    return parsed


def normalize_rule(rule: str | None) -> str | None:
    """Check a rule and return it in canonical form, or raise ValueError."""
    if rule is None or not rule.strip():
        return None
    rule = rule.strip().upper().removeprefix("RRULE:")
    if "DTSTART" in rule or "\n" in rule:
        raise ValueError("only a single RRULE is allowed; the due date is the start")
    if "COUNT=" in rule:
        # COUNT is counted from the start date, which moves with every copy,
        # so it would never run out. UNTIL does what people mean.
        raise ValueError("COUNT isn't supported; use UNTIL=YYYYMMDD to end a repeat")
    try:
        _parse(rule, date(2000, 1, 1))
    except (ValueError, TypeError) as e:
        raise ValueError(f"invalid repeat rule {rule!r}: {e}") from e
    return rule


def next_due(rule: str, due: date | None, today: date) -> date | None:
    """The due date for the next copy of a ticket, or None if the repeat has ended.

    Normally it's the next occurrence after the current due date. If that's
    already in the past (the ticket was finished late), skip ahead to the first
    occurrence from today on, so finishing late doesn't create overdue copies.
    """
    start = due or today
    r = _parse(rule, start)
    after = r.after(datetime.combine(start, time()))
    if after and after.date() < today:
        after = r.after(datetime.combine(today, time()), inc=True)
    return after.date() if after else None
