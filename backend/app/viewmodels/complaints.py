from datetime import timedelta, datetime
from secrets import token_hex
from ..errors import DomainError as HTTPException
from sqlalchemy import select
from .. import schemas as S
from ..models import Complaint, TimelineEvent, TestAttempt, Location, Building, now
from ..common import (
    get,
    serialize,
    location_check,
    complaint_access,
    support_check,
    audit,
    page,
    OPS,
)
from ..models.network import notify, operators, detect_incident

ALLOWED = {
    "submitted": {"reviewed"},
    "reviewed": set(),
    "assigned": {"in_progress"},
    "in_progress": {"resolved", "awaiting_user", "awaiting_external"},
    "awaiting_user": {"in_progress"},
    "awaiting_external": {"in_progress"},
    "resolved": {"closed", "reopened"},
    "closed": {"reopened"},
    "reopened": {"in_progress"},
}


def event(db, user, c, old, new, note, visibility="public", evidence=None):
    e = TimelineEvent(
        complaint_id=c.id,
        actor_id=user.id,
        old_status=old,
        new_status=new,
        note=note,
        visibility=visibility,
        evidence=evidence or {},
    )
    db.add(e)
    db.flush()
    audit(db, user, "complaint.updated", c, {"event_id": e.id, "old": old, "new": new})
    if visibility == "public":
        notify(
            db,
            [c.user_id],
            f"complaint:{c.id}:{e.id}",
            "Complaint update",
            f"{c.reference}: {note}",
        )
    return e


class ComplaintsViewModel:
    """Orchestrates use cases and prepares state consumed by API Views."""

    @staticmethod
    def create(data: S.ComplaintCreate, user=None, db=None):
        location_check(db, user, data.location_id, active=True)
        existing = db.scalar(
            select(Complaint).where(
                Complaint.user_id == user.id, Complaint.submission_id == data.submission_id
            )
        )
        if existing:
            # Classification may change the stored category; compare retry input to the original report.
            from ..models import Audit

            classification = db.scalar(
                select(Audit)
                .where(Audit.entity_id == existing.id, Audit.action == "ai.complaint_classified")
                .order_by(Audit.created_at)
            )
            original_category = (
                classification.details.get("original_category", existing.category)
                if classification
                else existing.category
            )
            if any(
                (
                    (original_category if k == "category" else getattr(existing, k))
                    != getattr(data, k)
                    for k in ("location_id", "category", "description", "test_id", "occurred_at")
                )
            ):
                raise HTTPException(409, "Submission ID already used for another complaint")
            return {**serialize(existing), "duplicate": True}
        if data.occurred_at and data.occurred_at > now() + timedelta(minutes=5):
            raise HTTPException(422, "Problem occurrence cannot be in the future")
        if data.test_id:
            a = get(db, TestAttempt, data.test_id)
            if a.user_id != user.id or a.location_id != data.location_id:
                raise HTTPException(422, "Evidence must be your test from this location")
            if a.created_at < now() - timedelta(hours=24):
                raise HTTPException(422, "Evidence must be less than 24 hours old")
            if a.status not in ("completed", "partial", "failed"):
                raise HTTPException(422, "Evidence test has not finished")
        c = Complaint(**data.model_dump(), user_id=user.id, reference="CMP-" + token_hex(6).upper())
        db.add(c)
        db.flush()
        from .ai import classify_complaint

        classify_complaint(db, user, c, automatic=True)
        event(db, user, c, None, "submitted", "Complaint received")
        notify(
            db,
            operators(db, user.campus_id),
            "new-complaint:" + c.id,
            "New network complaint",
            f"{c.reference}: {c.category}",
        )
        db.flush()
        detect_incident(db, c.location_id)
        return {**serialize(c), "duplicate": False}

    @staticmethod
    def listing(
        location_id: str | None = None,
        building_id: str | None = None,
        category: S.Category | None = None,
        status: str | None = None,
        assignee_id: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
        user=None,
        db=None,
    ):
        from ..models.reporting import normalize_range

        since, until = normalize_range(since, until)
        q = (
            select(Complaint)
            .join(Location)
            .join(Building)
            .where(Building.campus_id == user.campus_id)
        )
        if user.role not in OPS:
            q = q.where(Complaint.user_id == user.id)
        if location_id:
            q = q.where(Complaint.location_id == location_id)
        if building_id:
            q = q.where(Location.building_id == building_id)
        if category:
            q = q.where(Complaint.category == category)
        if status:
            q = q.where(Complaint.status == status)
        if assignee_id:
            q = q.where(Complaint.assignee_id == assignee_id)
        if since:
            q = q.where(Complaint.created_at >= since)
        if until:
            q = q.where(Complaint.created_at < until)
        return page(db, q.order_by(Complaint.created_at.desc()), limit, offset)

    @staticmethod
    def detail(id: str, user=None, db=None):
        c = get(db, Complaint, id)
        complaint_access(db, user, c)
        q = select(TimelineEvent).where(TimelineEvent.complaint_id == id)
        if user.role not in OPS:
            q = q.where(TimelineEvent.visibility == "public")
        return {
            **serialize(c),
            "events": [serialize(e) for e in db.scalars(q.order_by(TimelineEvent.created_at))],
        }

    @staticmethod
    def assign(id: str, data: S.Assignment, user=None, db=None):
        c = db.scalar(select(Complaint).where(Complaint.id == id).with_for_update())
        if not c:
            raise HTTPException(404, "Complaint not found")
        complaint_access(db, user, c)
        support_check(db, user, data.assignee_id)
        if c.status not in (
            "reviewed",
            "assigned",
            "in_progress",
            "reopened",
            "awaiting_user",
            "awaiting_external",
        ):
            raise HTTPException(409, "Review complaint before assignment")
        old = c.status
        c.assignee_id = data.assignee_id
        if old == "reviewed":
            c.status = "assigned"
        e = event(db, user, c, old, c.status, data.note)
        notify(db, [data.assignee_id], f"assigned:{c.id}:{e.id}", "Complaint assigned", c.reference)
        return serialize(c)

    @staticmethod
    def transition(id: str, data: S.ComplaintTransition, user=None, db=None):
        c = db.scalar(select(Complaint).where(Complaint.id == id).with_for_update())
        if not c:
            raise HTTPException(404, "Complaint not found")
        complaint_access(db, user, c)
        if user.role not in OPS and data.status != "reopened":
            raise HTTPException(403, "Only IT staff can change this status")
        if data.status != "resolved" and data.status not in ALLOWED.get(c.status, set()):
            raise HTTPException(409, f"Invalid transition from {c.status} to {data.status}")
        evidence = {}
        if data.status == "resolved":
            if c.status in ("resolved", "closed"):
                return serialize(c)
            if not c.assignee_id:
                c.assignee_id = user.id
            evidence = {"resolution_method": "manual", "resolved_by": user.id}
            c.resolved_at = now()
        elif data.status == "reopened":
            c.resolved_at = None
        old = c.status
        c.status = data.status
        event(db, user, c, old, c.status, data.note, evidence=evidence)
        return serialize(c)

    @staticmethod
    def note(id: str, data: S.Note, user=None, db=None):
        c = get(db, Complaint, id)
        complaint_access(db, user, c)
        if data.visibility == "internal" and user.role not in OPS:
            raise HTTPException(403, "Internal notes are restricted to IT")
        return serialize(event(db, user, c, None, None, data.note, data.visibility))
