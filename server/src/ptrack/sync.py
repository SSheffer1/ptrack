"""Field-level sync with last-write-wins.

Every edit, whether from the phone or the web UI, is a *change*: "set field F of
entity E to value V at time T, from device D". Each change is appended to the
`change` table (the log) and applied to the regular tables (the current state).

Conflicts: when two devices edit the same field, the change with the later
timestamp wins, and the device id breaks exact ties. Edits to different fields
of the same ticket never conflict. Losing changes stay in the log as history.

Devices download with a cursor: "give me every change with seq > N".

The server also makes changes of its own, logged under device "server":
ticket numbers, completion dates, and the next copy of a recurring ticket.
"""

import json
import time
import uuid
from collections.abc import Callable
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, TypeAdapter, ValidationError
from pydantic_core import to_jsonable_python
from sqlmodel import Session, SQLModel, col, select

from .models import Change, Comment, Item, ItemType, Project, Status
from .recurrence import next_due, normalize_rule
from .reminders import normalize_reminders

ENTITIES: dict[str, type[SQLModel]] = {"project": Project, "item": Item, "comment": Comment}

# Fields only the server may set.
SERVER_FIELDS = {"id", "owner_id", "created_at", "updated_at", "number", "next_number", "next_id"}

# Extra checks beyond the column type. Each returns the cleaned value or raises ValueError.
FIELD_CHECKS: dict[tuple[str, str], Callable[[Any], Any]] = {
    ("item", "repeat"): normalize_rule,
    ("item", "reminders"): normalize_reminders,
}

# Device ids used by the server itself; phones can't claim them.
SERVER_DEVICE = "server"
WEB_DEVICE = "web"
RESERVED_DEVICES = {SERVER_DEVICE, WEB_DEVICE}


class SyncError(ValueError):
    pass


class ChangeIn(BaseModel):
    entity: Literal["project", "item", "comment"]
    entity_id: str
    field: str
    value: Any
    ts: int  # ms since epoch; must increase with every change a device makes


class ChangeOut(ChangeIn):
    seq: int
    device_id: str


_clock = 0


def now_ms() -> int:
    """Timestamp for server-side edits: wall clock, but never behind any change already seen.

    A simplified hybrid logical clock. An edit made on the web right after a phone
    synced is ordered after the phone's changes even if the phone's clock runs fast.
    """
    global _clock
    _clock = max(time.time_ns() // 1_000_000, _clock + 1)
    return _clock


def _observe(ts: int) -> None:
    global _clock
    _clock = max(_clock, ts)


def apply_changes(session: Session, owner_id: str, device_id: str, changes: list[ChangeIn]) -> None:
    """Log and apply a batch of changes. All or nothing: a bad change rejects the batch."""
    try:
        status_changed: dict[str, int] = {}  # item id → time of its status change
        completed_on_set: set[str] = set()  # items whose completion date the device set itself
        for change in changes:
            applied = _apply_one(session, owner_id, device_id, change)
            if applied and change.entity == "item":
                if change.field == "status":
                    status_changed[change.entity_id] = change.ts
                elif change.field == "completed_on":
                    completed_on_set.add(change.entity_id)
            _observe(change.ts)
        _update_completion_dates(session, status_changed, completed_on_set)
        _spawn_next_occurrences(session, owner_id, list(status_changed))
        _assign_ticket_numbers(session, owner_id)
        session.commit()
    except Exception:
        session.rollback()
        raise


def _apply_one(session: Session, owner_id: str, device_id: str, change: ChangeIn) -> bool:
    """Log one change and apply it if it's the newest. Returns whether it was applied."""
    model = ENTITIES[change.entity]
    if change.field in SERVER_FIELDS or change.field not in model.model_fields:
        raise SyncError(f"{change.entity}.{change.field} is not writable")
    try:
        value = TypeAdapter(model.model_fields[change.field].annotation).validate_python(change.value)
        if check := FIELD_CHECKS.get((change.entity, change.field)):
            value = check(value)
    except (ValidationError, ValueError) as e:
        raise SyncError(f"bad value for {change.entity}.{change.field}: {e}") from e

    same_field = select(Change).where(
        Change.entity == change.entity,
        Change.entity_id == change.entity_id,
        Change.field == change.field,
    )
    if session.exec(same_field.where(Change.ts == change.ts, Change.device_id == device_id)).first():
        return False  # already have it: the device retried after a dropped connection
    latest = session.exec(same_field.order_by(col(Change.ts).desc(), col(Change.device_id).desc())).first()

    session.add(
        Change(
            owner_id=owner_id,
            entity=change.entity,
            entity_id=change.entity_id,
            field=change.field,
            value=json.dumps(to_jsonable_python(value)),
            ts=change.ts,
            device_id=device_id,
        )
    )
    if latest and (latest.ts, latest.device_id) > (change.ts, device_id):
        return False  # a newer edit already won; keep this one only as history

    row = session.get(model, change.entity_id)
    if row is None:
        row = model(id=change.entity_id, owner_id=owner_id, created_at=change.ts)
        session.add(row)
    elif row.owner_id != owner_id:
        raise SyncError(f"{change.entity} {change.entity_id} not found")
    setattr(row, change.field, value)
    row.updated_at = max(row.updated_at, change.ts)
    return True


def _server_set(session: Session, row: SQLModel, entity: str, field: str, value: Any) -> None:
    """Set a field as the server and log it, so devices pick it up on their next sync."""
    ts = now_ms()
    setattr(row, field, value)
    row.updated_at = ts  # type: ignore[attr-defined]
    session.add(
        Change(
            owner_id=row.owner_id,  # type: ignore[attr-defined]
            entity=entity,
            entity_id=row.id,  # type: ignore[attr-defined]
            field=field,
            value=json.dumps(to_jsonable_python(value)),
            ts=ts,
            device_id=SERVER_DEVICE,
        )
    )


def _update_completion_dates(session: Session, status_changed: dict[str, int], explicit: set[str]) -> None:
    """Keep `completed_on` in step with the status, unless the device set it itself.

    Marking done records the day it happened: the day of the edit, not the day
    it synced, so offline completions get the right date. Reopening clears it.
    """
    for item_id, ts in status_changed.items():
        item = session.get(Item, item_id)
        if item is None or item_id in explicit:
            continue
        if item.status == Status.done and item.completed_on is None:
            _server_set(session, item, "item", "completed_on", datetime.fromtimestamp(ts / 1000).date())
        elif item.status != Status.done and item.completed_on is not None:
            _server_set(session, item, "item", "completed_on", None)


# Copied from a recurring ticket to its next occurrence.
RECURRING_FIELDS = ["type", "project_id", "title", "body", "priority", "labels", "due_time", "repeat", "reminders"]


def _spawn_next_occurrences(session: Session, owner_id: str, status_changed: list[str]) -> None:
    """For each recurring ticket just marked done, create the next one.

    The server does this (not the device), so a ticket completed on two phones
    still produces only one next copy. `next_id` remembers the copy, so marking
    the ticket done again later doesn't create another.
    """
    for item_id in status_changed:
        item = session.get(Item, item_id)
        if not item or item.status != Status.done or item.deleted or not item.repeat or item.next_id:
            continue
        due = next_due(item.repeat, item.due, date.today())
        if due is None:
            continue  # the repeat has ended (UNTIL passed)
        copy = Item(id=str(uuid.uuid4()), owner_id=owner_id, created_at=now_ms())
        session.add(copy)
        for field in RECURRING_FIELDS:
            _server_set(session, copy, "item", field, getattr(item, field))
        _server_set(session, copy, "item", "status", Status.todo)
        _server_set(session, copy, "item", "due", due)
        _server_set(session, item, "item", "next_id", copy.id)


def _assign_ticket_numbers(session: Session, owner_id: str) -> None:
    """Give new tickets their per-project number (the 12 in HOME-12).

    Devices can't pick numbers themselves, because two offline phones would both
    choose HOME-13. Tickets arrive without one and the server hands numbers out
    here in creation order. Each assignment is logged as a change, so devices
    learn the number on their next sync.
    """
    session.flush()
    pending = session.exec(
        select(Item)
        .where(
            Item.owner_id == owner_id,
            Item.type == ItemType.ticket,
            col(Item.number).is_(None),
            col(Item.project_id).is_not(None),
        )
        .order_by(col(Item.created_at))
    ).all()
    for item in pending:
        project = session.get(Project, item.project_id)
        if project is None or project.owner_id != owner_id:
            continue  # the project hasn't synced yet; try again next batch
        _server_set(session, item, "item", "number", project.next_number)
        project.next_number += 1


def to_out(change: Change) -> ChangeOut:
    assert change.seq is not None
    return ChangeOut(
        seq=change.seq,
        entity=change.entity,  # type: ignore[arg-type]
        entity_id=change.entity_id,
        field=change.field,
        value=json.loads(change.value),
        ts=change.ts,
        device_id=change.device_id,
    )


def changes_since(session: Session, owner_id: str, since: int, limit: int) -> list[ChangeOut]:
    rows = session.exec(
        select(Change)
        .where(Change.owner_id == owner_id, col(Change.seq) > since)
        .order_by(col(Change.seq))
        .limit(limit)
    ).all()
    return [to_out(c) for c in rows]
