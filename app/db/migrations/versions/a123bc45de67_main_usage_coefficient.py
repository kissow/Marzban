"""Persist local main-core billing multiplier; existing traffic is untouched."""
from alembic import op
import sqlalchemy as sa

revision = "a123bc45de67"
down_revision = "9012ab34cd56"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("system") as batch:
        batch.add_column(sa.Column("usage_coefficient", sa.Float(), nullable=False,
                                   server_default="1.0"))


def downgrade():
    with op.batch_alter_table("system") as batch:
        batch.drop_column("usage_coefficient")
