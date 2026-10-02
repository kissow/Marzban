"""store per-device protocol credentials for direct Node enforcement

Revision ID: 6d7e8f9012ab
Revises: 4a9d2e8b7c61
"""

from alembic import op
import sqlalchemy as sa


revision = "6d7e8f9012ab"
down_revision = "4a9d2e8b7c61"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user_devices", sa.Column("credentials", sa.JSON(), nullable=False, server_default="{}"))


def downgrade() -> None:
    op.drop_column("user_devices", "credentials")
