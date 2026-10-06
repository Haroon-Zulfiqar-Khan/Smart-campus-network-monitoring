from ..errors import DomainError as HTTPException
from sqlalchemy import select
from .. import schemas as S
from ..models import Campus, Building, Location, User, Endpoint, Threshold, Audit, LoginSession
from ..common import get, campus_check, location_check, serialize, page, audit
from ..models.network import thresholds
from ..security import passwords


class AdminViewModel:
    """Orchestrates use cases and prepares state consumed by API Views."""

    @staticmethod
    def building(data: S.BuildingCreate, user=None, db=None):
        campus_check(user, data.campus_id)
        get(db, Campus, data.campus_id)
        b = Building(**data.model_dump())
        db.add(b)
        db.flush()
        audit(db, user, "building.created", b)
        return serialize(b)

    @staticmethod
    def location(data: S.LocationCreate, user=None, db=None):
        b = get(db, Building, data.building_id)
        campus_check(user, b.campus_id)
        location = Location(**data.model_dump())
        db.add(location)
        db.flush()
        audit(db, user, "location.created", location)
        return serialize(location)

    @staticmethod
    def update_location(id: str, data: S.LocationUpdate, user=None, db=None):
        location = location_check(db, user, id)
        for k, v in data.model_dump(exclude_none=True).items():
            setattr(location, k, v)
        audit(db, user, "location.updated", location, data.model_dump(exclude_none=True))
        return serialize(location)

    @staticmethod
    def users(limit: int = 50, offset: int = 0, user=None, db=None):
        return page(
            db,
            select(User).where(User.campus_id == user.campus_id).order_by(User.created_at.desc()),
            limit,
            offset,
        )

    @staticmethod
    def create_user(data: S.UserCreate, user=None, db=None):
        campus_check(user, data.campus_id)
        if db.scalar(select(User.id).where(User.email == data.email)):
            raise HTTPException(409, "Email already registered")
        u = User(
            **data.model_dump(exclude={"password"}), password_hash=passwords.hash(data.password)
        )
        db.add(u)
        db.flush()
        audit(db, user, "user.created", u)
        return serialize(u)

    @staticmethod
    def update_user(id: str, data: S.UserUpdate, user=None, db=None):
        u = get(db, User, id)
        campus_check(user, u.campus_id)
        if id == user.id and (data.is_active is False or (data.role and data.role != "admin")):
            raise HTTPException(409, "Cannot deactivate or demote your own administrator account")
        for k, v in data.model_dump(exclude_none=True).items():
            setattr(u, k, v)
        for s in db.scalars(select(LoginSession).where(LoginSession.user_id == u.id)):
            s.revoked = True
        audit(db, user, "user.updated", u, data.model_dump(exclude_none=True))
        return serialize(u)

    @staticmethod
    def config(user=None, db=None):
        return serialize(thresholds(db, user.campus_id))

    @staticmethod
    def set_thresholds(data: S.ThresholdConfig, user=None, db=None):
        db.scalar(select(Campus).where(Campus.id == user.campus_id).with_for_update())
        current = thresholds(db, user.campus_id)
        row = Threshold(
            campus_id=user.campus_id, version=current.version + 1, config=data.model_dump()
        )
        db.add(row)
        db.flush()
        audit(db, user, "thresholds.version_created", row)
        return serialize(row)

    @staticmethod
    def endpoint(data: S.EndpointCreate, user=None, db=None):
        campus_check(user, data.campus_id)
        e = Endpoint(**data.model_dump())
        db.add(e)
        db.flush()
        audit(db, user, "endpoint.created", e)
        return serialize(e)

    @staticmethod
    def endpoint_update(id: str, data: S.EndpointUpdate, user=None, db=None):
        e = get(db, Endpoint, id)
        campus_check(user, e.campus_id)
        for k, v in data.model_dump(exclude_none=True).items():
            setattr(e, k, v)
        audit(db, user, "endpoint.updated", e, data.model_dump(exclude_none=True))
        return serialize(e)

    @staticmethod
    def audit_list(limit: int = 50, offset: int = 0, user=None, db=None):
        q = (
            select(Audit)
            .join(User, User.id == Audit.actor_id)
            .where(User.campus_id == user.campus_id)
            .order_by(Audit.created_at.desc())
        )
        return page(db, q, limit, offset)
