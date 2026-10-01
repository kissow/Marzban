"""add per-user device limit settings and device registry

Revision ID: 4a9d2e8b7c61
Revises: 3d1184b99029
"""

from alembic import op
import sqlalchemy as sa


revision = "4a9d2e8b7c61"
down_revision = "3d1184b99029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("device_limit", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "users",
        sa.Column(
            "device_limit_mode",
            sa.Enum("hwid", name="devicelimitmode"),
            nullable=False,
            server_default="hwid",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "device_limit_action",
            sa.Enum("log_only", "reject_new", name="devicelimitaction"),
            nullable=False,
            server_default="log_only",
        ),
    )
    op.create_table(
        "user_devices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("hwid_hash", sa.String(length=64), nullable=False),
        sa.Column("first_seen", sa.DateTime(), nullable=False),
        sa.Column("last_seen", sa.DateTime(), nullable=False),
        sa.Column("last_ip", sa.String(length=255), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("device_os", sa.String(length=64), nullable=True),
        sa.Column("device_model", sa.String(length=128), nullable=True),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("user_id", "hwid_hash", name="uq_user_devices_user_hwid"),
    )
    op.create_index("ix_user_devices_user_id", "user_devices", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_user_devices_user_id", table_name="user_devices")
    op.drop_table("user_devices")
    op.drop_column("users", "device_limit_action")
    op.drop_column("users", "device_limit_mode")
    op.drop_column("users", "device_limit")
    # PostgreSQL keeps named enum types after their last column is removed;
    # SQLite/MySQL do not create standalone types, so only clean them up on
    # PostgreSQL.
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TYPE IF EXISTS devicelimitaction")
        op.execute("DROP TYPE IF EXISTS devicelimitmode")
