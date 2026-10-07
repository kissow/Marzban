"""Add optional main-server TCP relays; existing users/nodes/hosts unchanged."""
from alembic import op
import sqlalchemy as sa

revision = "8f9012ab34cd"
down_revision = "7e8f9012ab34"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "node_relays",
        sa.Column("node_id", sa.Integer(), sa.ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("entry_address", sa.String(253), nullable=False),
        sa.Column("listen_port", sa.Integer(), nullable=False),
        sa.Column("inbound_tag", sa.String(256), nullable=False),
        sa.Column("allocation", sa.String(8), nullable=False, server_default="auto"),
        sa.UniqueConstraint("listen_port", name="uq_node_relays_listen_port"),
    )


def downgrade():
    op.drop_table("node_relays")
