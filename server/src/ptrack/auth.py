"""Accounts and sign-in.

Accounts are created by an admin (no public sign-up; this is for a family).
Each device signs in once with username + password and gets its own random
token, sent on every request as `Authorization: Bearer <token>`. The server
stores only a hash of each token, so a copy of the database can't be used to
sign in, and any one device can be signed out without affecting the others.

Passwords are hashed with scrypt from Python's standard library.
"""

import hashlib
import hmac
import secrets
import time
import uuid
from dataclasses import dataclass, field
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, col, select

from .db import SessionDep
from .models import DeviceToken, Member, Role, User

SCRYPT_N, SCRYPT_R, SCRYPT_P = 2**14, 8, 1
MIN_PASSWORD = 8
USERNAME_PATTERN = r"^[a-z][a-z0-9_.-]{1,31}$"


def wall_ms() -> int:
    return time.time_ns() // 1_000_000


# --- Passwords and tokens ---------------------------------------------------------


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=32)
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, n, r, p, salt, digest = stored.split("$")
    except ValueError:
        return False  # no password set
    if algorithm != "scrypt":
        return False
    actual = hashlib.scrypt(
        password.encode(), salt=bytes.fromhex(salt), n=int(n), r=int(r), p=int(p), dklen=len(digest) // 2
    )
    return hmac.compare_digest(actual.hex(), digest)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def issue_token(session: Session, user: User, device_name: str) -> str:
    token = secrets.token_urlsafe(32)
    now = wall_ms()
    session.add(
        DeviceToken(
            id=str(uuid.uuid4()),
            user_id=user.id,
            token_hash=_token_hash(token),
            name=device_name,
            created_at=now,
            last_used_at=now,
        )
    )
    return token


def create_user(session: Session, username: str, display_name: str, password: str, is_admin: bool = False) -> User:
    user = User(
        id=str(uuid.uuid4()),
        username=username.lower(),
        display_name=display_name or username,
        password_hash=hash_password(password),
        is_admin=is_admin,
        created_at=wall_ms(),
    )
    session.add(user)
    return user


# --- Who's asking ---------------------------------------------------------------------


@dataclass
class Actor:
    """The signed-in user making a request, and their role in each of their projects."""

    user: User
    token_id: str
    roles: dict[str, Role] = field(default_factory=dict)  # project id → role

    @property
    def id(self) -> str:
        return self.user.id


def load_roles(session: Session, user_id: str) -> dict[str, Role]:
    return {m.project_id: m.role for m in session.exec(select(Member).where(Member.user_id == user_id)).all()}


def current_actor(session: SessionDep, authorization: Annotated[str | None, Header()] = None) -> Actor:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "sign in required", headers={"WWW-Authenticate": "Bearer"})
    device = session.exec(
        select(DeviceToken).where(DeviceToken.token_hash == _token_hash(authorization.removeprefix("Bearer ")))
    ).first()
    user = session.get(User, device.user_id) if device and not device.revoked else None
    if device is None or user is None or user.disabled:
        raise HTTPException(401, "signed out (or the account was disabled)", headers={"WWW-Authenticate": "Bearer"})
    if wall_ms() - device.last_used_at > 60_000:  # don't write on every request
        device.last_used_at = wall_ms()
        session.commit()
    return Actor(user=user, token_id=device.id, roles=load_roles(session, user.id))


ActorDep = Annotated[Actor, Depends(current_actor)]


def require_admin(actor: ActorDep) -> Actor:
    if not actor.user.is_admin:
        raise HTTPException(403, "admins only")
    return actor


# --- Endpoints --------------------------------------------------------------------------


class UserRead(BaseModel):
    id: str
    username: str
    display_name: str
    is_admin: bool = False


def user_read(user: User) -> UserRead:
    return UserRead(id=user.id, username=user.username, display_name=user.display_name, is_admin=user.is_admin)


class LoginRequest(BaseModel):
    username: str
    password: str
    device_name: str = Field(default="", max_length=100)


class LoginResponse(BaseModel):
    token: str
    user: UserRead


public_router = APIRouter()  # no sign-in needed
router = APIRouter()  # signed-in user
admin_router = APIRouter(dependencies=[Depends(require_admin)])


@public_router.post("/auth/login")
def login(body: LoginRequest, session: SessionDep) -> LoginResponse:
    user = session.exec(select(User).where(User.username == body.username.strip().lower())).first()
    if user is None or user.disabled or not verify_password(body.password, user.password_hash):
        time.sleep(1)  # slow down password guessing
        raise HTTPException(401, "wrong username or password")
    token = issue_token(session, user, body.device_name or "unnamed device")
    session.commit()
    return LoginResponse(token=token, user=user_read(user))


@router.post("/auth/logout", status_code=204)
def logout(actor: ActorDep, session: SessionDep) -> None:
    device = session.get(DeviceToken, actor.token_id)
    if device:
        device.revoked = True
        session.commit()


@router.get("/me")
def me(actor: ActorDep) -> UserRead:
    return user_read(actor.user)


class PasswordChange(BaseModel):
    current: str
    new: str = Field(min_length=MIN_PASSWORD)


@router.post("/me/password", status_code=204)
def change_password(body: PasswordChange, actor: ActorDep, session: SessionDep) -> None:
    if not verify_password(body.current, actor.user.password_hash):
        raise HTTPException(403, "current password is wrong")
    actor.user.password_hash = hash_password(body.new)
    session.commit()


class DeviceRead(BaseModel):
    id: str
    name: str
    created_at: int
    last_used_at: int
    current: bool  # the device making this request


@router.get("/me/devices")
def my_devices(actor: ActorDep, session: SessionDep) -> list[DeviceRead]:
    devices = session.exec(
        select(DeviceToken)
        .where(DeviceToken.user_id == actor.id, col(DeviceToken.revoked).is_(False))
        .order_by(col(DeviceToken.last_used_at).desc())
    ).all()
    return [
        DeviceRead(id=d.id, name=d.name, created_at=d.created_at, last_used_at=d.last_used_at, current=d.id == actor.token_id)
        for d in devices
    ]


@router.delete("/me/devices/{device_id}", status_code=204)
def sign_out_device(device_id: str, actor: ActorDep, session: SessionDep) -> None:
    device = session.get(DeviceToken, device_id)
    if device is None or device.user_id != actor.id:
        raise HTTPException(404, "device not found")
    device.revoked = True
    session.commit()


# --- Admin: family accounts ------------------------------------------------------------------


class AdminUserRead(UserRead):
    disabled: bool
    created_at: int


class UserCreate(BaseModel):
    username: str = Field(pattern=USERNAME_PATTERN)
    display_name: str = ""
    password: str = Field(min_length=MIN_PASSWORD)
    is_admin: bool = False


class UserUpdate(BaseModel):
    display_name: str | None = None
    password: str | None = Field(default=None, min_length=MIN_PASSWORD)  # reset it
    disabled: bool | None = None
    is_admin: bool | None = None


def _admin_read(user: User) -> AdminUserRead:
    return AdminUserRead(**user_read(user).model_dump(), disabled=user.disabled, created_at=user.created_at)


@admin_router.get("/admin/users")
def list_users(session: SessionDep) -> list[AdminUserRead]:
    return [_admin_read(u) for u in session.exec(select(User).order_by(col(User.username))).all()]


@admin_router.post("/admin/users", status_code=201)
def add_user(body: UserCreate, session: SessionDep) -> AdminUserRead:
    if session.exec(select(User).where(User.username == body.username)).first():
        raise HTTPException(409, f"username {body.username} is taken")
    user = create_user(session, body.username, body.display_name, body.password, body.is_admin)
    session.commit()
    return _admin_read(user)


@admin_router.patch("/admin/users/{user_id}")
def update_user(user_id: str, body: UserUpdate, actor: ActorDep, session: SessionDep) -> AdminUserRead:
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(404, "user not found")
    if user.id == actor.id and (body.disabled or body.is_admin is False):
        raise HTTPException(400, "you can't disable yourself or remove your own admin rights")
    if body.display_name is not None:
        user.display_name = body.display_name
    if body.password is not None:
        user.password_hash = hash_password(body.password)
    if body.disabled is not None:
        user.disabled = body.disabled
    if body.is_admin is not None:
        user.is_admin = body.is_admin
    session.commit()
    return _admin_read(user)
