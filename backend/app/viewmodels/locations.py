from sqlalchemy import select
from ..models import Campus, Building, Location, Endpoint
from ..common import get, location_check, serialize
from ..models.network import location_health


class LocationsViewModel:
    """Orchestrates use cases and prepares state consumed by API Views."""

    @staticmethod
    def campus(user=None, db=None):
        return serialize(get(db, Campus, user.campus_id))

    @staticmethod
    def buildings(user=None, db=None):
        return [
            serialize(b)
            for b in db.scalars(
                select(Building).where(Building.campus_id == user.campus_id).order_by(Building.name)
            )
        ]

    @staticmethod
    def locations(
        building_id: str | None = None,
        include_inactive: bool = False,
        limit: int = 100,
        offset: int = 0,
        user=None,
        db=None,
    ):
        q = select(Location).join(Building).where(Building.campus_id == user.campus_id)
        if building_id:
            q = q.where(Location.building_id == building_id)
        if not include_inactive:
            q = q.where(Location.is_active.is_(True))
        from sqlalchemy import func

        total = db.scalar(select(func.count()).select_from(q.subquery()))
        return {
            "items": [
                location_health(db, location)
                for location in db.scalars(q.order_by(Location.name).limit(limit).offset(offset))
            ],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    @staticmethod
    def location(id: str, user=None, db=None):
        return location_health(db, location_check(db, user, id))

    @staticmethod
    def endpoints(user=None, db=None):
        return [
            serialize(e)
            for e in db.scalars(
                select(Endpoint).where(
                    Endpoint.campus_id == user.campus_id, Endpoint.is_active.is_(True)
                )
            )
        ]
