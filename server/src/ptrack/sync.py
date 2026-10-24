"""Field-level sync with last-write-wins, and who may change what.

Every edit, whether from the phone or the web UI, is a *change*: "set field F of
entity E to value V at time T, from device D". Each change is appended to the
`change` table (the log) and applied to the regular tables (the current state).

Conflicts: when two devices edit the same field, the change with the later
timestamp wins, and the device id breaks exact ties. Edits to different fields
of the same ticket never conflict. Losing changes stay in the log as history.

Each change belongs to a project (`Change.project_id`), and devices download
only the changes of projects their user is a member of: "every change with
seq > N in my projects". A person's preferences (entity "prefs") belong to
the scope "user:<their id>" instead, so only their own devices get them.

Permissions are checked per change. A change the user isn't allowed to make
(say, an edit made offline to a project they've since been removed from) is
*dropped*: not applied, not logged, and reported back so the device can
discard it. Malformed changes reject the whole batch instead.

The server also makes changes of its own, logged under device "server":
ticket numbers, completion dates, who created what, the next copy of a
recurring ticket, and renamed project keys when two collide.
"""

import json
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, TypeAdapter, ValidationError
from pydantic_core import to_jsonable_python
from sqlmodel import Session, SQLModel, col, select

from .auth import Actor
from . import prefs
from .models import Change, Comment, Item, ItemType, Member, Project, Role, Status, User, UserPrefs
from .recurrence import next_due, normalize_rule
from .reminders import normalize_reminders

ENTITIES: dict[str, type[SQLModel]] = {"project": Project, "item": Item, "comment": Comment, "prefs": UserPrefs}
# Projects first, so tickets created in the same batch can refer to them; then tickets, then comments.
ENTITY_ORDER = {"prefs": 0, "project": 0, "item": 1, "comment": 2}

# Fields only the server may set.
SERVER_FIELDS = {"id", "created_by", "created_at", "updated_at", "number", "next_number", "next_id"}

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
    """The batch is malformed; nothing in it is applied."""


class Denied(Exception):
    """The user may not make this change."""


class ChangeIn(BaseModel):
    entity: Literal["project", "item", "comment", "prefs"]
    entity_id: str
    field: str
    value: Any
    ts: int  # ms since epoch; must increase with every change a device makes


class ChangeOut(ChangeIn):
    seq: int
    device_id: str
    user_id: str  # who made it


class Dropped(BaseModel):
    """A change the server refused; the device should discard it."""

    entity: str
    entity_id: str
    field: str
    ts: int
    reason: str


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


@dataclass
class _Batch:
    """What a batch says about rows it creates, before those rows exist."""

    item_project: dict[str, str] = field(default_factory=dict)  # new item id → project id
    comment_item: dict[str, str] = field(default_factory=dict)  # new comment id → item id
    created: list[tuple[str, SQLModel]] = field(default_factory=list)  # rows created by this batch
    keys_changed: set[str] = field(default_factory=set)  # projects whose key was set

    @classmethod
    def scan(cls, changes: list[ChangeIn]) -> "_Batch":
        batch = cls()
        for c in changes:
            if c.entity == "item" and c.field == "project_id" and isinstance(c.value, str):
                batch.item_project.setdefault(c.entity_id, c.value)
            elif c.entity == "comment" and c.field == "item_id" and isinstance(c.value, str):
                batch.comment_item.setdefault(c.entity_id, c.value)
        return batch


def apply_changes(
    session: Session, actor: Actor, device_id: str, changes: list[ChangeIn], strict: bool = False
) -> list[Dropped]:
    """Log and apply a batch of changes, returning the ones the user wasn't allowed to make.

    strict=True (used by the REST API, which writes one thing at a time) refuses
    the whole batch on the first disallowed change by raising Denied instead.
    """
    try:
        batch = _Batch.scan(changes)
        dropped: list[Dropped] = []
        status_changed: dict[str, int] = {}  # item id → time of its status change
        completed_on_set: set[str] = set()  # items whose completion date the device set itself
        for change in sorted(changes, key=lambda c: ENTITY_ORDER[c.entity]):
            try:
                applied = _apply_one(session, actor, device_id, change, batch)
            except Denied as e:
                if strict:
                    raise
                dropped.append(Dropped(entity=change.entity, entity_id=change.entity_id, field=change.field, ts=change.ts, reason=str(e)))
                continue
            if applied and change.entity == "item":
                if change.field == "status":
                    status_changed[change.entity_id] = change.ts
                elif change.field == "completed_on":
                    completed_on_set.add(change.entity_id)
            _observe(change.ts)
        _finish_new_rows(session, actor, batch)
        _resolve_key_conflicts(session, batch.keys_changed)
        _update_completion_dates(session, status_changed, completed_on_set)
        _spawn_next_occurrences(session, list(status_changed))
        _assign_ticket_numbers(session)
        session.commit()
        return dropped
    except Exception:
        session.rollback()
        raise


def _apply_one(session: Session, actor: Actor, device_id: str, change: ChangeIn, batch: _Batch) -> bool:
    """Check, log and apply one change. Returns whether it took effect (it may lose to a newer edit)."""
    model = ENTITIES[change.entity]
    if change.entity != "prefs" and (change.field in SERVER_FIELDS or change.field not in model.model_fields):
        raise SyncError(f"{change.entity}.{change.field} is not writable")
    try:
        if change.entity == "prefs":
            value = prefs.validate(change.field, change.value)
        else:
            value = TypeAdapter(model.model_fields[change.field].annotation).validate_python(change.value)
            if check := FIELD_CHECKS.get((change.entity, change.field)):
                value = check(value)
    except (ValidationError, ValueError) as e:
        raise SyncError(f"bad value for {change.entity}.{change.field}: {e}") from e

    scope = _scope(session, change, batch)
    _check_permission(session, actor, change, value, scope)

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
            project_id=scope,
            user_id=actor.id,
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
        row = model(id=change.entity_id, created_at=change.ts)
        session.add(row)
        if change.entity != "prefs":
            batch.created.append((change.entity, row))
    if isinstance(row, UserPrefs):
        # One JSON object of name → value; assign a new dict so the change is saved.
        row.values = {k: v for k, v in {**row.values, change.field: to_jsonable_python(value)}.items() if v is not None}
    else:
        setattr(row, change.field, value)
    row.updated_at = max(row.updated_at, change.ts)  # type: ignore[attr-defined]
    if change.entity == "project" and change.field == "key":
        batch.keys_changed.add(change.entity_id)
    return True


def _scope(session: Session, change: ChangeIn, batch: _Batch) -> str:
    """The project a change belongs to ("" if it can't be told)."""
    if change.entity == "prefs":
        return prefs.scope(change.entity_id)
    if change.entity == "project":
        return change.entity_id
    if change.entity == "item":
        return _item_project(session, change.entity_id, batch)
    comment = session.get(Comment, change.entity_id)
    item_id = comment.item_id if comment and comment.item_id else batch.comment_item.get(change.entity_id, "")
    return _item_project(session, item_id, batch)


def _item_project(session: Session, item_id: str, batch: _Batch) -> str:
    item = session.get(Item, item_id)
    return (item.project_id if item and item.project_id else None) or batch.item_project.get(item_id, "")


def _check_permission(session: Session, actor: Actor, change: ChangeIn, value: Any, scope: str) -> None:
    if change.entity == "prefs":
        if change.entity_id != actor.id:
            raise Denied("you can only change your own preferences")
        return
    project = session.get(Project, scope) if scope else None
    role = actor.roles.get(scope)

    if change.entity == "project":
        if project is None:
            # A new project: its creator owns it.
            if scope not in actor.roles:
                actor.roles[scope] = Role.owner
                session.add(Member(project_id=scope, user_id=actor.id, role=Role.owner, added_at=now_ms()))
            return
        if role != Role.owner:
            raise Denied("only the project's owner can rename or delete it")
        return

    if not scope:
        raise Denied("a ticket must belong to a project")
    if role is None or project is None or project.deleted:
        raise Denied("you're not a member of this project")

    if change.entity == "item":
        item = session.get(Item, change.entity_id)
        if change.field == "deleted" and role != Role.owner:
            raise Denied("only the project's owner can delete tickets")
        if change.field == "project_id" and item and item.project_id and value != item.project_id:
            raise Denied("tickets can't move to another project")
        if change.field == "assignee_id" and value is not None and not session.get(Member, (scope, value)):
            raise Denied("the assignee must be a member of the project")
        if change.field == "reminders" and item and item.created_by and notified_user(item) != actor.id:
            raise Denied("only the person the ticket is assigned to can change its reminders")
    else:
        comment = session.get(Comment, change.entity_id)
        if comment and comment.created_by and comment.created_by != actor.id and role != Role.owner:
            raise Denied("only the author can edit a comment")


def notified_user(item: Item) -> str | None:
    """Who gets this ticket's reminders: the assignee, or else whoever created it."""
    return item.assignee_id or item.created_by


def _row_scope(session: Session, entity: str, row: SQLModel) -> str:
    if isinstance(row, Project):
        return row.id
    if isinstance(row, Item):
        return row.project_id or ""
    assert isinstance(row, Comment)
    item = session.get(Item, row.item_id)
    return item.project_id or "" if item else ""


def server_set(session: Session, actor: Actor, entity: str, row: SQLModel, field: str, value: Any) -> None:
    """Set a field as the server and log it, so devices pick it up on their next sync."""
    ts = now_ms()
    setattr(row, field, value)
    row.updated_at = ts  # type: ignore[attr-defined]
    session.add(
        Change(
            project_id=_row_scope(session, entity, row),
            user_id=actor.id,
            entity=entity,
            entity_id=row.id,  # type: ignore[attr-defined]
            field=field,
            value=json.dumps(to_jsonable_python(value)),
            ts=ts,
            device_id=SERVER_DEVICE,
        )
    )


def _finish_new_rows(session: Session, actor: Actor, batch: _Batch) -> None:
    for entity, row in batch.created:
        server_set(session, actor, entity, row, "created_by", actor.id)


def _resolve_key_conflicts(session: Session, project_ids: set[str]) -> None:
    """Project keys are unique on the server. If two people picked the same one
    (say, both offline), the later project gets a number added: GYM → GYM2."""
    for project_id in project_ids:
        project = session.get(Project, project_id)
        if project is None or project.deleted:
            continue
        taken = {
            p.key
            for p in session.exec(select(Project).where(Project.id != project.id, col(Project.deleted).is_(False))).all()
        }
        if project.key not in taken:
            continue
        base = project.key[:8]
        n = 2
        while f"{base}{n}" in taken:
            n += 1
        owner = session.exec(select(Member).where(Member.project_id == project.id, Member.role == Role.owner)).first()
        user = session.get(User, owner.user_id) if owner else None
        if user:
            server_set(session, Actor(user=user, token_id=""), "project", project, "key", f"{base}{n}")


def _update_completion_dates(session: Session, status_changed: dict[str, int], explicit: set[str]) -> None:
    """Keep `completed_on` in step with the status, unless the device set it itself.

    Marking done records the day it happened: the day of the edit, not the day
    it synced, so offline completions get the right date. Reopening clears it.
    """
    for item_id, ts in status_changed.items():
        item = session.get(Item, item_id)
        if item is None or item_id in explicit:
            continue
        actor = _system_actor(session, item)
        if item.status == Status.done and item.completed_on is None:
            server_set(session, actor, "item", item, "completed_on", datetime.fromtimestamp(ts / 1000).date())
        elif item.status != Status.done and item.completed_on is not None:
            server_set(session, actor, "item", item, "completed_on", None)


def _system_actor(session: Session, item: Item) -> Actor:
    """Server changes are credited to the ticket's creator."""
    user = session.get(User, item.created_by) if item.created_by else None
    return Actor(user=user or User(id=item.created_by or ""), token_id="")


# Copied from a recurring ticket to its next occurrence.
RECURRING_FIELDS = [
    "type", "project_id", "title", "body", "priority", "labels", "due_time", "repeat", "reminders", "assignee_id",
    "created_by",
]


def _spawn_next_occurrences(session: Session, status_changed: list[str]) -> None:
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
        actor = _system_actor(session, item)
        copy = Item(id=str(uuid.uuid4()), created_at=now_ms())
        session.add(copy)
        copy.project_id = item.project_id  # so the copy's changes are logged under the right project
        for name in RECURRING_FIELDS:
            server_set(session, actor, "item", copy, name, getattr(item, name))
        server_set(session, actor, "item", copy, "status", Status.todo)
        server_set(session, actor, "item", copy, "due", due)
        server_set(session, actor, "item", item, "next_id", copy.id)


def _assign_ticket_numbers(session: Session) -> None:
    """Give new tickets their per-project number (the 12 in HOME-12).

    Devices can't pick numbers themselves, because two offline phones would both
    choose HOME-13. Tickets arrive without one and the server hands numbers out
    here in creation order. Each assignment is logged as a change, so devices
    learn the number on their next sync.
    """
    session.flush()
    pending = session.exec(
        select(Item)
        .where(Item.type == ItemType.ticket, col(Item.number).is_(None), col(Item.project_id).is_not(None))
        .order_by(col(Item.created_at))
    ).all()
    for item in pending:
        project = session.get(Project, item.project_id)
        if project is None:
            continue  # the project hasn't synced yet; try again next batch
        server_set(session, _system_actor(session, item), "item", item, "number", project.next_number)
        project.next_number += 1


def unassign_member(session: Session, actor: Actor, project_id: str, user_id: str) -> None:
    """When someone leaves a project, their tickets there become unassigned."""
    for item in session.exec(select(Item).where(Item.project_id == project_id, Item.assignee_id == user_id)).all():
        server_set(session, actor, "item", item, "assignee_id", None)


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
        user_id=change.user_id,
    )


def changes_since(session: Session, project_ids: list[str], since: int, limit: int) -> list[ChangeOut]:
    rows = session.exec(
        select(Change)
        .where(col(Change.project_id).in_(project_ids), col(Change.seq) > since)
        .order_by(col(Change.seq))
        .limit(limit)
    ).all()
    return [to_out(c) for c in rows]
