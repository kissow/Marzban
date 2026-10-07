"""Add source selection; existing relay records remain on the main server."""
from alembic import op
import sqlalchemy as sa

revision = "9012ab34cd56"
down_revision = "8f9012ab34cd"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("node_relays") as batch:
        batch.add_column(sa.Column("source", sa.String(8), nullable=False, server_default="main"))
        batch.add_column(sa.Column("source_node_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_node_relays_source", "nodes", ["source_node_id"], ["id"], ondelete="SET NULL")


def downgrade():
    with op.batch_alter_table("node_relays") as batch:
        batch.drop_constraint("fk_node_relays_source", type_="foreignkey")
        batch.drop_column("source_node_id")
        batch.drop_column("source")
