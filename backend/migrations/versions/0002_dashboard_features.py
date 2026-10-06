"""Map coordinates, policies and maintenance notes for existing dashboards."""

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("locations", sa.Column("latitude", sa.Float(), nullable=True))
    op.add_column("locations", sa.Column("longitude", sa.Float(), nullable=True))
    op.add_column(
        "locations",
        sa.Column("user_reported", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_table(
        "role_policies",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("campus_id", sa.String(36), sa.ForeignKey("campuses.id"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("permissions", sa.JSON(), nullable=False),
        sa.UniqueConstraint("campus_id", "role"),
    )
    op.create_table(
        "maintenance_notes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("location_id", sa.String(36), sa.ForeignKey("locations.id"), nullable=False),
        sa.Column("author_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
    )
    op.create_index("ix_role_policies_created_at", "role_policies", ["created_at"])
    op.create_index("ix_maintenance_notes_created_at", "maintenance_notes", ["created_at"])
    op.create_index("ix_maintenance_notes_location_id", "maintenance_notes", ["location_id"])


def downgrade():
    op.drop_table("maintenance_notes")
    op.drop_table("role_policies")
    op.drop_column("locations", "user_reported")
    op.drop_column("locations", "longitude")
    op.drop_column("locations", "latitude")
