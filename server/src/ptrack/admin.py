"""Command line for managing accounts on the server.

    uv run ptrack-admin create-user alex --name "Alex" --admin
    uv run ptrack-admin set-password alex
    uv run ptrack-admin rename-user owner alex
    uv run ptrack-admin list-users

Uses the same database as the server (PTRACK_DB). Passwords are asked for
interactively, so they don't end up in your shell history.
"""

import argparse
import getpass
import re
import sys

from sqlmodel import Session, select

from .auth import MIN_PASSWORD, USERNAME_PATTERN, create_user, hash_password
from .db import engine, init_db
from .models import User


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
    args = parser.parse_args()

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
        else:
            for u in session.exec(select(User).order_by(User.username)).all():
                flags = ", ".join(f for f, on in [("admin", u.is_admin), ("disabled", u.disabled), ("no password", not u.password_hash)] if on)
                print(f"{u.username:<20} {u.display_name:<20} {flags}")
        session.commit()
