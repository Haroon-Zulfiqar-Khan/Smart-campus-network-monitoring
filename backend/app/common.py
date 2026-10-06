from datetime import datetime, timezone
from .errors import DomainError as HTTPException
from sqlalchemy import select, func
from .models import Building, Location, User, Audit

OPS = {"support", "manager", "admin"}


def get(db, model, id):
    value = db.get(model, id)
    if not value:
        raise HTTPException(404, f"{model.__name__} not found")
    return value


def campus_check(user, campus_id):
    if user.campus_id != campus_id:
        raise HTTPException(403, "Outside your campus scope")


def location_check(db, user, id, active=False):
    location = get(db, Location, id)
    building = get(db, Building, location.building_id)
    campus_check(user, building.campus_id)
    if active and not location.is_active:
        raise HTTPException(409, "Location is inactive")
    return location


def audit(db, user, action, entity, details=None):
    db.add(
        Audit(
            actor_id=user.id if user else None,
            action=action,
            entity_id=entity.id,
            details=details or {},
        )
    )


def serialize(obj, exclude=()):
    result = {}
    for column in obj.__table__.columns:
        key = column.name
        if key in exclude or key in {"password_hash", "refresh_hash"}:
            continue
        value = getattr(obj, key)
        if isinstance(value, datetime):
            value = value.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
        result[key] = value
    return result


def page(db, query, limit, offset):
    total = db.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
    values = db.scalars(query.limit(limit).offset(offset)).all()
    return {
        "items": [serialize(v) for v in values],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def complaint_access(db, user, complaint):
    location_check(db, user, complaint.location_id)
    if user.role not in OPS and complaint.user_id != user.id:
        raise HTTPException(403, "This complaint belongs to another user")


def support_check(db, user, id):
    person = get(db, User, id)
    campus_check(user, person.campus_id)
    if not person.is_active or person.role not in OPS:
        raise HTTPException(422, "Assignee must be active IT staff")
    return person
