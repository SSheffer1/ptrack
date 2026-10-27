"""Command line for managing accounts on the server. See server/COMMANDS.md.

Uses the same database as the server (ptrack.toml or PTRACK_DB). Passwords are
asked for interactively, so they don't end up in your shell history.
"""

import argparse
import getpass
import re
import sys

from sqlmodel import Session, col, select

from . import backup
from .auth import MIN_PASSWORD, USERNAME_PATTERN, create_user, hash_password
from .config import describe, settings
from .db import engine, init_db
from .models import DeviceToken, Member, Project, Role, User
from .sync import now_ms


def _ask_password() -> str:
    while True:
        password = getpass.getpass("Password: ")
        if len(password) < MIN_PASSWORD:
            print(f"Use at least {MIN_PASSWORD} characters.")
        elif getpass.getpass("Again: ") != password:
            print("Those didn't match.")
        else:
            return password


def _find(session: Session, username: str) -> User:
    user = session.exec(select(User).where(User.username == username.lower())).first()
    if user is None:
        sys.exit(f"no user named {username!r}")
    return user


def _set_role(session: Session, key: str, username: str, role: Role) -> str:
    user = _find(session, username)
    project = session.exec(select(Project).where(Project.key == key.upper(), col(Project.deleted).is_(False))).first()
    if project is None:
        sys.exit(f"no project with key {key!r}")
    member = session.get(Member, (project.id, user.id))
    if member is None:
        session.add(Member(project_id=project.id, user_id=user.id, role=role, added_at=now_ms()))
        user.epoch += 1  # their devices download the project on their next sync
        return f"added {user.username} to {project.key} as {role.value}"
    if member.role == Role.owner and role != Role.owner:
        owners = session.exec(select(Member).where(Member.project_id == project.id, Member.role == Role.owner)).all()
        if len(owners) == 1:
            sys.exit(f"{user.username} is {project.key}'s only owner; make someone else owner first")
    member.role = role  # devices pick up the new role on their next sync
    return f"{user.username} is now {role.value} of {project.key}"


def main() -> None:
    parser = argparse.ArgumentParser(prog="ptrack-admin", description="Manage ptrack accounts.")
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create-user", help="add an account")
    create.add_argument("username")
    create.add_argument("--name", default="", help="display name (default: the username)")
    create.add_argument("--admin", action="store_true", help="can manage accounts")
    commands.add_parser("set-password", help="set or reset a password").add_argument("username")
    rename = commands.add_parser("rename-user", help="change a username")
    rename.add_argument("old")
    rename.add_argument("new")
    commands.add_parser("list-users", help="show all accounts")
    commands.add_parser("disable-user", help="block sign-in and sign out everywhere").add_argument("username")
    commands.add_parser("enable-user", help="allow a disabled account again").add_argument("username")
    admin = commands.add_parser("set-admin", help="let an account manage accounts (or --off to stop)")
    admin.add_argument("username")
    admin.add_argument("--off", action="store_true")
    commands.add_parser("sign-out", help="sign an account out on all its devices").add_argument("username")
    role = commands.add_parser("set-role", help="make someone an owner or editor of a project (adds them if needed)")
    role.add_argument("project", help="project key, e.g. HOME")
    role.add_argument("username")
    role.add_argument("role", choices=[r.value for r in Role])
    commands.add_parser("show-config", help="print the server settings in effect (ptrack.toml + defaults)")
    commands.add_parser("backup", help="back up the database now (and delete expired backups)")
    commands.add_parser("list-backups", help="show the backups")
    args = parser.parse_args()

    if args.command == "show-config":
        print(describe(settings), end="")
        return
    if args.command in ("backup", "list-backups"):
        db = backup.database_path()
        if db is None:
            sys.exit("backups only work with a SQLite database")
        if args.command == "backup":
            print(f"written {backup.backup_now()}")
        for when, path in backup.list_backups(backup.backup_folder(db)):
            print(f"{when:%Y-%m-%d %H:%M}  {path.stat().st_size / 1024:8.0f} KB  {path}")
        return

    init_db()  # make sure the schema is current
    with Session(engine) as session:
        if args.command == "create-user":
            if not re.match(USERNAME_PATTERN, args.username):
                sys.exit("usernames are lowercase letters, digits, . _ - (2-32 characters, starting with a letter)")
            if session.exec(select(User).where(User.username == args.username)).first():
                sys.exit(f"username {args.username!r} is taken")
            user = create_user(session, args.username, args.name, _ask_password(), args.admin)
            print(f"created {user.username}{' (admin)' if user.is_admin else ''}")
        elif args.command == "set-password":
            user = _find(session, args.username)
            user.password_hash = hash_password(_ask_password())
            print(f"password set for {user.username}")
        elif args.command == "rename-user":
            user = _find(session, args.old)
            if not re.match(USERNAME_PATTERN, args.new):
                sys.exit("usernames are lowercase letters, digits, . _ - (2-32 characters, starting with a letter)")
            user.username = args.new
            print(f"renamed {args.old} → {args.new}")
        elif args.command in ("disable-user", "enable-user"):
            user = _find(session, args.username)
            user.disabled = args.command == "disable-user"
            print(f"{user.username} {'disabled' if user.disabled else 'enabled'}")
        elif args.command == "set-admin":
            user = _find(session, args.username)
            user.is_admin = not args.off
            print(f"{user.username} is {'now' if user.is_admin else 'no longer'} an admin")
        elif args.command == "set-role":
            print(_set_role(session, args.project, args.username, Role(args.role)))
        elif args.command == "sign-out":
            user = _find(session, args.username)
            devices = session.exec(
                select(DeviceToken).where(DeviceToken.user_id == user.id, col(DeviceToken.revoked).is_(False))
            ).all()
            for d in devices:
                d.revoked = True
            print(f"signed {user.username} out of {len(devices)} device(s)")
        else:
            for u in session.exec(select(User).order_by(User.username)).all():
                flags = ", ".join(f for f, on in [("admin", u.is_admin), ("disabled", u.disabled), ("no password", not u.password_hash)] if on)
                print(f"{u.username:<20} {u.display_name:<20} {flags}")
        session.commit()
