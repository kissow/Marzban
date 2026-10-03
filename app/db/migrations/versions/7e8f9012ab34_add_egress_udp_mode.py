"""Add per-Node UDP handling without replacing existing egress settings.

Revision ID: 7e8f9012ab34
Revises: 6d7e8f9012ab
"""
from alembic import op
import sqlalchemy as sa

revision = "7e8f9012ab34"
down_revision = "6d7e8f9012ab"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("node_egress", sa.Column("udp_mode", sa.String(16),
                                         nullable=False, server_default="legacy"))


def downgrade():
    op.drop_column("node_egress", "udp_mode")
