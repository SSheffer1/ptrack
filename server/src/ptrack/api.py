"""HTTP API.

The REST endpoints are what the desktop browser uses while online. They don't
write to tables directly: each edit becomes field-level changes and goes through
the same `apply_changes` path that phone sync uses. That makes the change log
the single record of everything that happened, and it doubles as ticket history.

Every endpoint acts as the signed-in user (see auth.py) and only sees projects
they're a member of. Project membership is managed here, online only.
"""

import re
import uuid
from datetime import date, datetime, time
from typing import Annotated, Any, Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlmodel import Session, col, select

from .auth import Actor, ActorDep, UserRead, load_roles, user_read
from .db import SessionDep
from .models import Change, Comment, Item, ItemType, Member, Priority, Project, Role, Status, User
from .sync import (
    RESERVED_DEVICES,
    WEB_DEVICE,
    ChangeIn,
    ChangeOut,
    Denied,
    Dropped,
    SyncError,
    apply_changes,
    changes_since,
    now_ms,
    to_out,
    unassign_member,
)

SYNC_PAGE_SIZE = 1000
KEY_RE = re.compile(r"^([A-Z][A-Z0-9]{0,9})-(\d+)$")
PROJECT_KEY_PATTERN = r"^[A-Z][A-Z0-9]{0,9}$"

router = APIRouter()


def _write(session: Session, actor: Actor, entity: str, entity_id: str, fields: dict[str, Any]) -> None:
    ts = now_ms()
    changes = [ChangeIn(entity=entity, entity_id=entity_id, field=k, value=v, ts=ts) for k, v in fields.items()]  # type: ignore[arg-type]
    try:
        apply_changes(session, actor, WEB_DEVICE, changes, strict=True)
    except SyncError as e:
        raise HTTPException(400, str(e)) from e
    except Denied as e:
        raise HTTPException(403, str(e)) from e


# --- Projects ---------------------------------------------------------------


class ProjectRead(BaseModel):
    id: str
    key: str
    name: str
    role: Role  # yours


class ProjectCreate(BaseModel):
    key: str = Field(pattern=PROJECT_KEY_PATTERN)
    name: str = Field(min_length=1)


class ProjectUpdate(BaseModel):
    key: str | None = Field(default=None, pattern=PROJECT_KEY_PATTERN)
    name: str | None = Field(default=None, min_length=1)


def _visible_projects(session: Session, actor: Actor) -> list[Project]:
    return list(
        session.exec(
            select(Project).where(col(Project.id).in_(list(actor.roles)), col(Project.deleted).is_(False))
        ).all()
    )


def _project_by_key(session: Session, actor: Actor, key: str) -> Project | None:
    return next((p for p in _visible_projects(session, actor) if p.key == key), None)


def _get_project(session: Session, actor: Actor, key: str) -> Project:
    project = _project_by_key(session, actor, key)
    if project is None:
        raise HTTPException(404, f"project {key} not found")
    return project


def _key_taken(session: Session, key: str, except_id: str | None = None) -> bool:
    query = select(Project).where(Project.key == key, col(Project.deleted).is_(False))
    if except_id:
        query = query.where(Project.id != except_id)
    return session.exec(query).first() is not None


def _project_read(actor: Actor, p: Project) -> ProjectRead:
    return ProjectRead(id=p.id, key=p.key, name=p.name, role=actor.roles[p.id])


@router.get("/projects")
def list_projects(actor: ActorDep, session: SessionDep) -> list[ProjectRead]:
    return [_project_read(actor, p) for p in sorted(_visible_projects(session, actor), key=lambda p: p.key)]


@router.post("/projects", status_code=201)
def create_project(body: ProjectCreate, actor: ActorDep, session: SessionDep) -> ProjectRead:
    if _key_taken(session, body.key):
        raise HTTPException(409, f"project key {body.key} is already used")
    project_id = str(uuid.uuid4())
    _write(session, actor, "project", project_id, body.model_dump())
    return _project_read(actor, _get_project(session, actor, body.key))


@router.patch("/projects/{key}")
def update_project(key: str, body: ProjectUpdate, actor: ActorDep, session: SessionDep) -> ProjectRead:
    project = _get_project(session, actor, key)
    fields = body.model_dump(exclude_unset=True, exclude_none=True)
    if "key" in fields and _key_taken(session, fields["key"], except_id=project.id):
        raise HTTPException(409, f"project key {fields['key']} is already used")
    if fields:
        _write(session, actor, "project", project.id, fields)
    session.refresh(project)
    return _project_read(actor, project)


@router.delete("/projects/{key}", status_code=204)
def delete_project(key: str, actor: ActorDep, session: SessionDep) -> None:
    _write(session, actor, "project", _get_project(session, actor, key).id, {"deleted": True})


# --- Members ------------------------------------------------------------------


class MemberRead(BaseModel):
    project_id: str
    user_id: str
    username: str
    display_name: str
    role: Role


class MemberAdd(BaseModel):
    username: str
    role: Role = Role.editor


def _members(session: Session, project_id: str) -> list[MemberRead]:
    rows = session.exec(
        select(Member, User).where(Member.project_id == project_id, Member.user_id == User.id).order_by(col(User.username))
    ).all()
    return [
        MemberRead(project_id=m.project_id, user_id=u.id, username=u.username, display_name=u.display_name, role=m.role)
        for m, u in rows
    ]


def _bump_epoch(session: Session, user_id: str) -> None:
    """The user's devices will re-download everything on their next sync."""
    user = session.get(User, user_id)
    if user:
        user.epoch += 1


@router.get("/projects/{key}/members")
def list_members(key: str, actor: ActorDep, session: SessionDep) -> list[MemberRead]:
    return _members(session, _get_project(session, actor, key).id)


@router.post("/projects/{key}/members", status_code=201)
def add_member(key: str, body: MemberAdd, actor: ActorDep, session: SessionDep) -> list[MemberRead]:
    project = _get_project(session, actor, key)
    if actor.roles[project.id] != Role.owner:
        raise HTTPException(403, "only the project's owner can add members")
    user = session.exec(select(User).where(User.username == body.username.strip().lower())).first()
    if user is None or user.disabled:
        raise HTTPException(404, f"no account named {body.username}")
    if session.get(Member, (project.id, user.id)):
        raise HTTPException(409, f"{user.username} is already a member")
    session.add(Member(project_id=project.id, user_id=user.id, role=body.role, added_at=now_ms()))
    _bump_epoch(session, user.id)
    session.commit()
    return _members(session, project.id)


@router.delete("/projects/{key}/members/{user_id}", status_code=204)
def remove_member(key: str, user_id: str, actor: ActorDep, session: SessionDep) -> None:
    """The owner removes someone, or a member leaves (removes themself)."""
    project = _get_project(session, actor, key)
    if user_id != actor.id and actor.roles[project.id] != Role.owner:
        raise HTTPException(403, "only the project's owner can remove members")
    member = session.get(Member, (project.id, user_id))
    if member is None:
        raise HTTPException(404, "not a member")
    owners = session.exec(select(Member).where(Member.project_id == project.id, Member.role == Role.owner)).all()
    if member.role == Role.owner and len(owners) == 1:
        raise HTTPException(400, "a project needs an owner; delete the project instead")
    session.delete(member)
    unassign_member(session, actor, project.id, user_id)
    _bump_epoch(session, user_id)
    session.commit()


# --- Items (tickets) -----------------------------------------------------------


class ItemCreate(BaseModel):
    project: str  # project key, e.g. "HOME"
    title: str = Field(min_length=1)
    body: str = ""
    status: Status = Status.todo
    priority: Priority = Priority.none
    labels: list[str] = []
    due: date | None = None
    due_time: time | None = None
    repeat: str | None = None  # RRULE, e.g. "FREQ=WEEKLY;BYDAY=FR"
    assignee_id: str | None = None
    assigned_on: date | None = None  # leave out to use today
    reminders: list[str] | None = None  # None = default; see reminders.py


class ItemUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    body: str | None = None
    status: Status | None = None
    priority: Priority | None = None
    labels: list[str] | None = None
    due: date | None = None
    due_time: time | None = None
    repeat: str | None = None
    assignee_id: str | None = None  # null = unassigned
    assigned_on: date | None = None  # null = back to the created date
    completed_on: date | None = None
    reminders: list[str] | None = None  # null = back to the default


class ItemRead(BaseModel):
    id: str
    key: str | None  # e.g. "HOME-12"; None until the server assigns a number
    project_id: str | None
    type: ItemType
    number: int | None
    title: str
    body: str
    status: Status
    priority: Priority
    labels: list[str]
    due: date | None
    due_time: time | None
    repeat: str | None
    next_id: str | None  # set once a recurring ticket is done: its next copy
    created_by: str | None
    assignee_id: str | None
    assigned_on: date | None  # only if set by hand
    assigned: date  # assigned_on, or else the day it was created
    completed_on: date | None
    reminders: list[str] | None  # None = default
    created_at: int
    updated_at: int


def _read(session: Session, item: Item) -> ItemRead:
    project = session.get(Project, item.project_id) if item.project_id else None
    key = f"{project.key}-{item.number}" if project and item.number else None
    assigned = item.assigned_on or datetime.fromtimestamp(item.created_at / 1000).date()
    return ItemRead(**item.model_dump(), key=key, assigned=assigned)


def _find_item(session: Session, actor: Actor, ref: str) -> Item:
    """Look an item up by key ("HOME-12") or by id, among the user's projects."""
    item: Item | None
    if m := KEY_RE.match(ref):
        project = _project_by_key(session, actor, m.group(1))
        item = project and session.exec(
            select(Item).where(Item.project_id == project.id, Item.number == int(m.group(2)))
        ).first()
    else:
        item = session.get(Item, ref)
    project = session.get(Project, item.project_id) if item and item.project_id else None
    if not item or item.deleted or not project or project.deleted or project.id not in actor.roles:
        raise HTTPException(404, f"item {ref} not found")
    return item


def _find_and_read(session: Session, actor: Actor, ref: str) -> ItemRead:
    return _read(session, _find_item(session, actor, ref))


@router.get("/items")
def list_items(
    actor: ActorDep,
    session: SessionDep,
    project: str | None = None,
    status: Annotated[list[Status] | None, Query()] = None,
    label: str | None = None,
    q: str | None = None,
    due_from: date | None = None,
    due_to: date | None = None,
    completed_from: date | None = None,
    completed_to: date | None = None,
    assignee: Literal["me"] | None = None,  # "me" = assigned to me, or unassigned and created by me
    sort: Literal["created", "due", "completed"] = "created",
) -> list[ItemRead]:
    project_ids = [p.id for p in _visible_projects(session, actor)]
    if project:
        project_ids = [_get_project(session, actor, project).id]
    query = select(Item).where(col(Item.project_id).in_(project_ids), col(Item.deleted).is_(False))
    if status:
        query = query.where(col(Item.status).in_(status))
    if q:
        query = query.where(col(Item.title).ilike(f"%{q}%") | col(Item.body).ilike(f"%{q}%"))
    if due_from:
        query = query.where(col(Item.due) >= due_from)
    if due_to:
        query = query.where(col(Item.due) <= due_to)
    if completed_from:
        query = query.where(col(Item.completed_on) >= completed_from)
    if completed_to:
        query = query.where(col(Item.completed_on) <= completed_to)
    if assignee == "me":
        query = query.where(
            (Item.assignee_id == actor.id) | (col(Item.assignee_id).is_(None) & (Item.created_by == actor.id))
        )
    order = {
        "created": [col(Item.created_at)],
        # Undated tickets last; same-day tickets by time, untimed last.
        "due": [col(Item.due).is_(None), col(Item.due), col(Item.due_time).is_(None), col(Item.due_time)],
        # Most recently finished first; unfinished last.
        "completed": [col(Item.completed_on).is_(None), col(Item.completed_on).desc(), col(Item.updated_at).desc()],
    }[sort]
    items = session.exec(query.order_by(*order)).all()
    if label:  # labels are a JSON list; filtering in Python is fine at personal scale
        items = [i for i in items if label in i.labels]
    return [_read(session, i) for i in items]


@router.post("/items", status_code=201)
def create_item(body: ItemCreate, actor: ActorDep, session: SessionDep) -> ItemRead:
    project = _get_project(session, actor, body.project)
    item_id = str(uuid.uuid4())
    fields = body.model_dump(mode="json", exclude={"project"})
    _write(session, actor, "item", item_id, {"type": ItemType.ticket, "project_id": project.id, **fields})
    return _find_and_read(session, actor, item_id)


@router.get("/items/{ref}")
def get_item(ref: str, actor: ActorDep, session: SessionDep) -> ItemRead:
    return _find_and_read(session, actor, ref)


@router.patch("/items/{ref}")
def update_item(ref: str, body: ItemUpdate, actor: ActorDep, session: SessionDep) -> ItemRead:
    item = _find_item(session, actor, ref)
    fields = body.model_dump(mode="json", exclude_unset=True)
    if fields:
        _write(session, actor, "item", item.id, fields)
    return _find_and_read(session, actor, item.id)


@router.delete("/items/{ref}", status_code=204)
def delete_item(ref: str, actor: ActorDep, session: SessionDep) -> None:
    item = _find_item(session, actor, ref)
    _write(session, actor, "item", item.id, {"deleted": True})


@router.get("/items/{ref}/history")
def item_history(ref: str, actor: ActorDep, session: SessionDep) -> list[ChangeOut]:
    item = _find_item(session, actor, ref)
    changes = session.exec(
        select(Change).where(Change.entity == "item", Change.entity_id == item.id).order_by(col(Change.ts))
    ).all()
    return [to_out(c) for c in changes]


# --- Comments ----------------------------------------------------------------


class CommentCreate(BaseModel):
    body: str = Field(min_length=1)


@router.get("/items/{ref}/comments")
def list_comments(ref: str, actor: ActorDep, session: SessionDep) -> list[Comment]:
    item = _find_item(session, actor, ref)
    return list(
        session.exec(
            select(Comment)
            .where(Comment.item_id == item.id, col(Comment.deleted).is_(False))
            .order_by(col(Comment.created_at))
        ).all()
    )


@router.post("/items/{ref}/comments", status_code=201)
def add_comment(ref: str, body: CommentCreate, actor: ActorDep, session: SessionDep) -> Comment:
    item = _find_item(session, actor, ref)
    comment_id = str(uuid.uuid4())
    _write(session, actor, "comment", comment_id, {"item_id": item.id, "body": body.body})
    comment = session.get(Comment, comment_id)
    assert comment is not None
    return comment


# --- People -------------------------------------------------------------------


def visible_users(session: Session, actor: Actor) -> list[User]:
    """You, plus everyone who shares a project with you."""
    ids = set(session.exec(select(Member.user_id).where(col(Member.project_id).in_(list(actor.roles)))).all())
    ids.add(actor.id)
    return list(session.exec(select(User).where(col(User.id).in_(ids)).order_by(col(User.username))).all())


@router.get("/users")
def list_visible_users(actor: ActorDep, session: SessionDep) -> list[UserRead]:
    return [user_read(u) for u in visible_users(session, actor)]


# --- Sync (phone app) -----------------------------------------------------------


class SyncRequest(BaseModel):
    device_id: str = Field(min_length=1)
    since: int = 0  # cursor from the previous sync; 0 = everything
    epoch: int = -1  # the user's epoch from the previous sync; -1 = first sync
    changes: list[ChangeIn] = []


class MembershipRead(BaseModel):
    project_id: str
    user_id: str
    role: Role


class SyncResponse(BaseModel):
    changes: list[ChangeOut]
    cursor: int  # pass back as `since` next time
    more: bool  # true if there are more changes; sync again right away
    dropped: list[Dropped]  # your changes the server refused; discard them
    reset: bool  # your projects changed: forget downloaded data, keep unsent edits, start again from these changes
    epoch: int  # pass back next time
    me: UserRead
    users: list[UserRead]  # everyone you share a project with
    members: list[MembershipRead]  # who's in each of your projects


@router.post("/sync")
def sync(body: SyncRequest, actor: ActorDep, session: SessionDep) -> SyncResponse:
    """Upload this device's changes, then download everything newer than `since`.

    The download includes the device's own changes. That's harmless (applying a
    change twice gives the same result) and keeps the protocol simple.
    """
    if body.device_id in RESERVED_DEVICES:
        raise HTTPException(400, f"device id {body.device_id!r} is reserved")
    try:
        dropped = apply_changes(session, actor, body.device_id, body.changes)
    except SyncError as e:
        raise HTTPException(400, str(e)) from e

    actor.roles = load_roles(session, actor.id)
    session.refresh(actor.user)
    reset = body.epoch != actor.user.epoch
    since = 0 if reset else body.since
    changes = changes_since(session, list(actor.roles), since, SYNC_PAGE_SIZE)
    memberships = session.exec(select(Member).where(col(Member.project_id).in_(list(actor.roles)))).all()
    return SyncResponse(
        changes=changes,
        cursor=changes[-1].seq if changes else since,
        more=len(changes) == SYNC_PAGE_SIZE,
        dropped=dropped,
        reset=reset,
        epoch=actor.user.epoch,
        me=user_read(actor.user),
        users=[user_read(u) for u in visible_users(session, actor)],
        members=[MembershipRead(project_id=m.project_id, user_id=m.user_id, role=m.role) for m in memberships],
    )
