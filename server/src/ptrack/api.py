"""HTTP API.

The REST endpoints are what the desktop browser uses while online. They don't
write to tables directly: each edit becomes field-level changes and goes through
the same `apply_changes` path that phone sync uses. That makes the change log
the single record of everything that happened, and it doubles as ticket history.
"""

import re
import uuid
from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlmodel import Session, col, select

from .db import get_session
from .models import Change, Comment, Item, ItemType, Priority, Project, Status
from .sync import (
    RESERVED_DEVICES,
    WEB_DEVICE,
    ChangeIn,
    ChangeOut,
    SyncError,
    apply_changes,
    changes_since,
    now_ms,
    to_out,
)

OWNER_ID = "owner"  # single user until login lands (Milestone 6)
SYNC_PAGE_SIZE = 1000
KEY_RE = re.compile(r"^([A-Z][A-Z0-9]{0,9})-(\d+)$")

router = APIRouter()
SessionDep = Annotated[Session, Depends(get_session)]


def _write(session: Session, entity: str, entity_id: str, fields: dict[str, Any]) -> None:
    ts = now_ms()
    changes = [ChangeIn(entity=entity, entity_id=entity_id, field=k, value=v, ts=ts) for k, v in fields.items()]  # type: ignore[arg-type]
    try:
        apply_changes(session, OWNER_ID, WEB_DEVICE, changes)
    except SyncError as e:
        raise HTTPException(400, str(e)) from e


# --- Projects ---------------------------------------------------------------


class ProjectCreate(BaseModel):
    key: str = Field(pattern=r"^[A-Z][A-Z0-9]{0,9}$")
    name: str = Field(min_length=1)


def _project_by_key(session: Session, key: str) -> Project | None:
    return session.exec(
        select(Project).where(Project.owner_id == OWNER_ID, Project.key == key, col(Project.deleted).is_(False))
    ).first()


@router.get("/projects")
def list_projects(session: SessionDep) -> list[Project]:
    return list(
        session.exec(
            select(Project)
            .where(Project.owner_id == OWNER_ID, col(Project.deleted).is_(False))
            .order_by(col(Project.key))
        ).all()
    )


@router.post("/projects", status_code=201)
def create_project(body: ProjectCreate, session: SessionDep) -> Project:
    if _project_by_key(session, body.key):
        raise HTTPException(409, f"project {body.key} already exists")
    project_id = str(uuid.uuid4())
    _write(session, "project", project_id, body.model_dump())
    project = session.get(Project, project_id)
    assert project is not None
    return project


# --- Items (tickets) -----------------------------------------------------------


class ItemCreate(BaseModel):
    project: str  # project key, e.g. "HOME"
    title: str = Field(min_length=1)
    body: str = ""
    status: Status = Status.todo
    priority: Priority = Priority.none
    labels: list[str] = []
    due: date | None = None


class ItemUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    body: str | None = None
    status: Status | None = None
    priority: Priority | None = None
    labels: list[str] | None = None
    due: date | None = None


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
    created_at: int
    updated_at: int


def _read(session: Session, item: Item) -> ItemRead:
    project = session.get(Project, item.project_id) if item.project_id else None
    key = f"{project.key}-{item.number}" if project and item.number else None
    return ItemRead(**item.model_dump(), key=key)


def _find_item(session: Session, ref: str) -> Item:
    """Look an item up by key ("HOME-12") or by id."""
    item: Item | None
    if m := KEY_RE.match(ref):
        project = _project_by_key(session, m.group(1))
        item = project and session.exec(
            select(Item).where(Item.project_id == project.id, Item.number == int(m.group(2)))
        ).first()
    else:
        item = session.get(Item, ref)
    if not item or item.owner_id != OWNER_ID or item.deleted:
        raise HTTPException(404, f"item {ref} not found")
    return item


def _find_and_read(session: Session, ref: str) -> ItemRead:
    return _read(session, _find_item(session, ref))


@router.get("/items")
def list_items(
    session: SessionDep,
    project: str | None = None,
    status: Annotated[list[Status] | None, Query()] = None,
    label: str | None = None,
    q: str | None = None,
) -> list[ItemRead]:
    query = select(Item).where(Item.owner_id == OWNER_ID, col(Item.deleted).is_(False))
    if project:
        p = _project_by_key(session, project)
        if not p:
            raise HTTPException(404, f"project {project} not found")
        query = query.where(Item.project_id == p.id)
    if status:
        query = query.where(col(Item.status).in_(status))
    if q:
        query = query.where(col(Item.title).ilike(f"%{q}%") | col(Item.body).ilike(f"%{q}%"))
    items = session.exec(query.order_by(col(Item.created_at))).all()
    if label:  # labels are a JSON list; filtering in Python is fine at personal scale
        items = [i for i in items if label in i.labels]
    return [_read(session, i) for i in items]


@router.post("/items", status_code=201)
def create_item(body: ItemCreate, session: SessionDep) -> ItemRead:
    project = _project_by_key(session, body.project)
    if not project:
        raise HTTPException(404, f"project {body.project} not found")
    item_id = str(uuid.uuid4())
    fields = body.model_dump(mode="json", exclude={"project"})
    _write(session, "item", item_id, {"type": ItemType.ticket, "project_id": project.id, **fields})
    return _find_and_read(session, item_id)


@router.get("/items/{ref}")
def get_item(ref: str, session: SessionDep) -> ItemRead:
    return _find_and_read(session, ref)


@router.patch("/items/{ref}")
def update_item(ref: str, body: ItemUpdate, session: SessionDep) -> ItemRead:
    item = _find_item(session, ref)
    fields = body.model_dump(mode="json", exclude_unset=True)
    if fields:
        _write(session, "item", item.id, fields)
    return _find_and_read(session, item.id)


@router.delete("/items/{ref}", status_code=204)
def delete_item(ref: str, session: SessionDep) -> None:
    item = _find_item(session, ref)
    _write(session, "item", item.id, {"deleted": True})


@router.get("/items/{ref}/history")
def item_history(ref: str, session: SessionDep) -> list[ChangeOut]:
    item = _find_item(session, ref)
    changes = session.exec(
        select(Change).where(Change.entity == "item", Change.entity_id == item.id).order_by(col(Change.ts))
    ).all()
    return [to_out(c) for c in changes]


# --- Comments ----------------------------------------------------------------


class CommentCreate(BaseModel):
    body: str = Field(min_length=1)


@router.get("/items/{ref}/comments")
def list_comments(ref: str, session: SessionDep) -> list[Comment]:
    item = _find_item(session, ref)
    return list(
        session.exec(
            select(Comment)
            .where(Comment.item_id == item.id, col(Comment.deleted).is_(False))
            .order_by(col(Comment.created_at))
        ).all()
    )


@router.post("/items/{ref}/comments", status_code=201)
def add_comment(ref: str, body: CommentCreate, session: SessionDep) -> Comment:
    item = _find_item(session, ref)
    comment_id = str(uuid.uuid4())
    _write(session, "comment", comment_id, {"item_id": item.id, "body": body.body})
    comment = session.get(Comment, comment_id)
    assert comment is not None
    return comment


# --- Sync (phone app) -----------------------------------------------------------


class SyncRequest(BaseModel):
    device_id: str = Field(min_length=1)
    since: int = 0  # cursor from the previous sync; 0 = everything
    changes: list[ChangeIn] = []


class SyncResponse(BaseModel):
    changes: list[ChangeOut]
    cursor: int  # pass back as `since` next time
    more: bool  # true if there are more changes; sync again right away


@router.post("/sync")
def sync(body: SyncRequest, session: SessionDep) -> SyncResponse:
    """Upload this device's changes, then download everything newer than `since`.

    The download includes the device's own changes. That's harmless (applying a
    change twice gives the same result) and keeps the protocol simple.
    """
    if body.device_id in RESERVED_DEVICES:
        raise HTTPException(400, f"device id {body.device_id!r} is reserved")
    try:
        apply_changes(session, OWNER_ID, body.device_id, body.changes)
    except SyncError as e:
        raise HTTPException(400, str(e)) from e
    changes = changes_since(session, OWNER_ID, body.since, SYNC_PAGE_SIZE)
    cursor = changes[-1].seq if changes else body.since
    return SyncResponse(changes=changes, cursor=cursor, more=len(changes) == SYNC_PAGE_SIZE)
