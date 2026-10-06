"""Initial schema; frozen metadata snapshot lives in this migration module."""

from alembic import op
import sqlalchemy as sa
from pathlib import Path
import json

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


# The generated DDL snapshot is versioned separately for SQLite/PostgreSQL.
# Schema is constructed from a frozen JSON manifest, not live application models.
def tables():
    manifest = json.loads((Path(__file__).parent / "0001_schema.json").read_text())
    metadata = sa.MetaData()
    for t in manifest:
        columns = []
        for c in t["columns"]:
            typ = {
                "string": lambda: sa.String(c["length"]),
                "text": sa.Text,
                "float": sa.Float,
                "integer": sa.Integer,
                "boolean": sa.Boolean,
                "datetime": sa.DateTime,
                "json": sa.JSON,
            }[c["type"]]()
            args = [sa.ForeignKey(c["foreign_key"])] if c.get("foreign_key") else []
            columns.append(
                sa.Column(
                    c["name"], typ, *args, primary_key=c["primary_key"], nullable=c["nullable"]
                )
            )
        constraints = [sa.UniqueConstraint(*keys) for keys in t["unique"]]
        table = sa.Table(t["name"], metadata, *columns, *constraints)
        for index in t["indexes"]:
            sa.Index(
                index["name"], *(table.c[name] for name in index["columns"]), unique=index["unique"]
            )
    return metadata


def upgrade():
    tables().create_all(op.get_bind())


def downgrade():
    tables().drop_all(op.get_bind())
