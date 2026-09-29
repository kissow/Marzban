"""Add per-node outbound configuration without changing existing node rows.

Revision ID: 3d1184b99029
Revises: 2b231de97dc3
"""

from alembic import op
import sqlalchemy as sa

revision = "3d1184b99029"
down_revision = "2b231de97dc3"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "node_egress",
        sa.Column("node_id", sa.Integer(), sa.ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("protocol", sa.String(8), nullable=False),
        sa.Column("server", sa.String(253), nullable=False),
        sa.Column("port", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(256), nullable=True),
        sa.Column("encrypted_password", sa.String(1024), nullable=True),
    )


def downgrade():
    op.drop_table("node_egress")
