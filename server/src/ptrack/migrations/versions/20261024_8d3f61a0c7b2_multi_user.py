"""multi-user: accounts, devices, project members, assignees

Revision ID: 8d3f61a0c7b2
Revises: 5b1e7c2d9a40
Create Date: 2026-10-24 14:00:00.000000

Existing single-user data (owner_id = "owner") becomes the data of an admin
account with id "owner" and no password; set one with
`uv run ptrack-admin set-password owner` (and rename it if you like).
"""

import time
from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = '8d3f61a0c7b2'
down_revision: str | None = '5b1e7c2d9a40'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

STR = sqlmodel.sql.sqltypes.AutoString


def upgrade() -> None:
    op.create_table('user',
    sa.Column('id', STR(), nullable=False),
    sa.Column('username', STR(), nullable=False),
    sa.Column('display_name', STR(), nullable=False),
    sa.Column('password_hash', STR(), nullable=False),
    sa.Column('is_admin', sa.Boolean(), nullable=False),
    sa.Column('disabled', sa.Boolean(), nullable=False),
    sa.Column('epoch', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_user_username'), ['username'], unique=True)

    op.create_table('devicetoken',
    sa.Column('id', STR(), nullable=False),
    sa.Column('user_id', STR(), nullable=False),
    sa.Column('token_hash', STR(), nullable=False),
    sa.Column('name', STR(), nullable=False),
    sa.Column('created_at', sa.Integer(), nullable=False),
    sa.Column('last_used_at', sa.Integer(), nullable=False),
    sa.Column('revoked', sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('devicetoken', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_devicetoken_token_hash'), ['token_hash'], unique=True)
        batch_op.create_index(batch_op.f('ix_devicetoken_user_id'), ['user_id'], unique=False)

    op.create_table('member',
    sa.Column('project_id', STR(), nullable=False),
    sa.Column('user_id', STR(), nullable=False),
    sa.Column('role', sa.Enum('owner', 'editor', name='role'), nullable=False),
    sa.Column('added_at', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('project_id', 'user_id')
    )
    with op.batch_alter_table('member', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_member_user_id'), ['user_id'], unique=False)

    # owner_id → created_by (project, item, comment) and → user_id (change).
    for table in ['project', 'item', 'comment']:
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.drop_index(f'ix_{table}_owner_id')
            batch_op.alter_column('owner_id', new_column_name='created_by', existing_type=sa.String(), nullable=True)
    with op.batch_alter_table('item', schema=None) as batch_op:
        batch_op.add_column(sa.Column('assignee_id', STR(), nullable=True))
    with op.batch_alter_table('change', schema=None) as batch_op:
        batch_op.drop_index('ix_change_owner_id')
        batch_op.alter_column('owner_id', new_column_name='user_id', existing_type=sa.String(), nullable=False)
        batch_op.add_column(sa.Column('project_id', STR(), nullable=False, server_default=''))
        batch_op.create_index(batch_op.f('ix_change_project_id'), ['project_id'], unique=False)

    # Existing data: give it to an "owner" admin account, owner of every project.
    conn = op.get_bind()
    if conn.execute(sa.text("SELECT COUNT(*) FROM project")).scalar():
        now = int(time.time() * 1000)
        conn.execute(sa.text(
            "INSERT INTO user (id, username, display_name, password_hash, is_admin, disabled, epoch, created_at) "
            "VALUES ('owner', 'owner', 'Owner', '', 1, 0, 0, :now)"), {"now": now})
        conn.execute(sa.text(
            "INSERT INTO member (project_id, user_id, role, added_at) SELECT id, 'owner', 'owner', :now FROM project"),
            {"now": now})
    # Each change belongs to a project, so only that project's members receive it.
    conn.execute(sa.text("UPDATE change SET project_id = entity_id WHERE entity = 'project'"))
    conn.execute(sa.text(
        "UPDATE change SET project_id = COALESCE((SELECT project_id FROM item WHERE item.id = change.entity_id), '') "
        "WHERE entity = 'item'"))
    conn.execute(sa.text(
        "UPDATE change SET project_id = COALESCE((SELECT item.project_id FROM comment JOIN item ON item.id = comment.item_id "
        "WHERE comment.id = change.entity_id), '') WHERE entity = 'comment'"))
    with op.batch_alter_table('change', schema=None) as batch_op:
        batch_op.alter_column('project_id', server_default=None, existing_type=sa.String(), existing_nullable=False)


def downgrade() -> None:
    with op.batch_alter_table('change', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_change_project_id'))
        batch_op.drop_column('project_id')
        batch_op.alter_column('user_id', new_column_name='owner_id', existing_type=sa.String(), nullable=False)
    with op.batch_alter_table('change', schema=None) as batch_op:
        batch_op.create_index('ix_change_owner_id', ['owner_id'], unique=False)
    with op.batch_alter_table('item', schema=None) as batch_op:
        batch_op.drop_column('assignee_id')
    for table in ['comment', 'item', 'project']:
        op.execute(f"UPDATE {table} SET created_by = 'owner' WHERE created_by IS NULL")
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.alter_column('created_by', new_column_name='owner_id', existing_type=sa.String(), nullable=False)
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.create_index(f'ix_{table}_owner_id', ['owner_id'], unique=False)
    with op.batch_alter_table('member', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_member_user_id'))
    op.drop_table('member')
    with op.batch_alter_table('devicetoken', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_devicetoken_user_id'))
        batch_op.drop_index(batch_op.f('ix_devicetoken_token_hash'))
    op.drop_table('devicetoken')
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_user_username'))
    op.drop_table('user')
