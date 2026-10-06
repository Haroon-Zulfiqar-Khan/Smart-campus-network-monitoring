from ..errors import DomainError as HTTPException
from sqlalchemy import select
from .. import schemas as S
from ..models import Maintenance, Notification, Location, Building
from ..common import get, serialize, location_check, audit, page
from ..models.network import notify, audience


class OperationsViewModel:
    """Orchestrates use cases and prepares state consumed by API Views."""

    @staticmethod
    def create(data: S.MaintenanceCreate, user=None, db=None):
        location_check(db, user, data.location_id)
        m = Maintenance(**data.model_dump(), owner_id=user.id)
        db.add(m)
        db.flush()
        audit(db, user, "maintenance.scheduled", m)
        notify(
            db,
            audience(db, user.campus_id),
            "maintenance:" + m.id,
            "Scheduled Wi-Fi maintenance",
            data.description,
        )
        return serialize(m)

    @staticmethod
    def maintenance(
        location_id: str | None = None, limit: int = 50, offset: int = 0, user=None, db=None
    ):
        q = (
            select(Maintenance)
            .join(Location)
            .join(Building)
            .where(Building.campus_id == user.campus_id)
        )
        if location_id:
            q = q.where(Maintenance.location_id == location_id)
        return page(db, q.order_by(Maintenance.starts_at.desc()), limit, offset)

    @staticmethod
    def cancel(id: str, user=None, db=None):
        m = get(db, Maintenance, id)
        location_check(db, user, m.location_id)
        m.cancelled = True
        audit(db, user, "maintenance.cancelled", m)
        notify(
            db,
            audience(db, user.campus_id),
            "maintenance-cancelled:" + m.id,
            "Maintenance cancelled",
            m.description,
        )
        return serialize(m)

    @staticmethod
    def notifications(
        unread_only: bool = False, limit: int = 50, offset: int = 0, user=None, db=None
    ):
        q = select(Notification).where(Notification.user_id == user.id)
        if unread_only:
            q = q.where(Notification.is_read.is_(False))
        return page(db, q.order_by(Notification.created_at.desc()), limit, offset)

    @staticmethod
    def mark_read(id: str, user=None, db=None):
        n = get(db, Notification, id)
        if n.user_id != user.id:
            raise HTTPException(403, "Notification belongs to another user")
        n.is_read = True
        return serialize(n)
