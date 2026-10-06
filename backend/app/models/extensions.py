from sqlalchemy import ForeignKey
from app.models.entities import Record
from app.db import Base
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Text, JSON, UniqueConstraint


class RolePolicy(Record, Base):
    __tablename__ = "role_policies"
    campus_id: Mapped[str] = mapped_column(ForeignKey("campuses.id"))
    role: Mapped[str] = mapped_column(String(20))
    permissions: Mapped[list] = mapped_column(JSON)
    __table_args__ = (UniqueConstraint("campus_id", "role"),)


class MaintenanceNote(Record, Base):
    __tablename__ = "maintenance_notes"
    location_id: Mapped[str] = mapped_column(ForeignKey("locations.id"), index=True)
    author_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    text: Mapped[str] = mapped_column(Text)


DEFAULTS = {
    "student": [],
    "staff": [],
    "support": ["tests", "complaints", "maintenance", "reports"],
    "manager": ["reports"],
    "admin": ["tests", "complaints", "maintenance", "locations", "reports"],
}


def allowed(db, user, capability):
    from sqlalchemy import select

    policy = db.scalar(
        select(RolePolicy).where(
            RolePolicy.campus_id == user.campus_id, RolePolicy.role == user.role
        )
    )
    return user.role == "admin" or capability in (
        policy.permissions if policy else DEFAULTS[user.role]
    )
