from ..errors import DomainError as HTTPException
from sqlalchemy import select
from .. import schemas as S
from ..models import Incident, TimelineEvent, Location, Building, now
from ..common import get, serialize, location_check, support_check, audit, page, OPS
from ..models.network import verify_recovery, thresholds, notify, audience

ALLOWED = {
    "suspected": {"confirmed", "dismissed"},
    "confirmed": {"investigating"},
    "investigating": {"monitoring_recovery"},
    "monitoring_recovery": {"resolved", "investigating"},
    "resolved": {"reopened"},
    "dismissed": {"reopened"},
    "reopened": {"investigating"},
}


class IncidentsViewModel:
    """Orchestrates use cases and prepares state consumed by API Views."""

    @staticmethod
    def listing(
        location_id: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
        user=None,
        db=None,
    ):
        q = (
            select(Incident)
            .join(Location)
            .join(Building)
            .where(Building.campus_id == user.campus_id)
        )
        if location_id:
            q = q.where(Incident.location_id == location_id)
        if status:
            q = q.where(Incident.status == status)
        result = page(db, q.order_by(Incident.created_at.desc()), limit, offset)
        if user.role not in OPS:
            for item in result["items"]:
                for key in ("evidence", "root_cause", "action_taken", "owner_id"):
                    item.pop(key, None)
        return result

    @staticmethod
    def detail(id: str, user=None, db=None):
        incident = get(db, Incident, id)
        location_check(db, user, incident.location_id)
        if user.role not in OPS:
            data = serialize(
                incident, exclude=("evidence", "root_cause", "action_taken", "owner_id")
            )
            return data
        return {
            **serialize(incident),
            "events": [
                serialize(e)
                for e in db.scalars(
                    select(TimelineEvent)
                    .where(TimelineEvent.incident_id == id)
                    .order_by(TimelineEvent.created_at)
                )
            ],
        }

    @staticmethod
    def assign(id: str, data: S.IncidentAssignment, user=None, db=None):
        incident = get(db, Incident, id)
        location_check(db, user, incident.location_id)
        support_check(db, user, data.owner_id)
        incident.owner_id = data.owner_id
        incident.severity = data.severity
        audit(db, user, "incident.assigned", incident, {"owner_id": data.owner_id})
        db.add(
            TimelineEvent(
                incident_id=id,
                actor_id=user.id,
                note="Incident owner and severity updated",
                visibility="internal",
            )
        )
        notify(
            db,
            [data.owner_id],
            f"incident-assigned:{id}:{data.owner_id}",
            "Incident assigned",
            "Review the assigned network incident",
        )
        return serialize(incident)

    @staticmethod
    def transition(id: str, data: S.IncidentTransition, user=None, db=None):
        incident = db.scalar(select(Incident).where(Incident.id == id).with_for_update())
        if not incident:
            raise HTTPException(404, "Incident not found")
        location_check(db, user, incident.location_id)
        if data.status not in ALLOWED.get(incident.status, set()):
            raise HTTPException(409, "Invalid incident transition")
        evidence = {}
        if data.status == "resolved":
            if not incident.owner_id or not data.root_cause or (not data.action_taken):
                raise HTTPException(
                    422,
                    "Resolution requires owner, root cause (or not confirmed), and action taken",
                )
            monitoring = db.scalar(
                select(TimelineEvent)
                .where(
                    TimelineEvent.incident_id == id,
                    TimelineEvent.new_status == "monitoring_recovery",
                )
                .order_by(TimelineEvent.created_at.desc())
            )
            evidence = verify_recovery(
                db,
                incident.location_id,
                data.verification_test_ids,
                monitoring.created_at if monitoring else incident.created_at,
                thresholds(db, user.campus_id).config["recovery_users"],
            )
            incident.active_key = None
            incident.resolved_at = now()
            incident.resolution_note = data.note
            incident.root_cause = data.root_cause
            incident.action_taken = data.action_taken
        elif data.status == "dismissed":
            incident.active_key = None
            incident.resolved_at = now()
            incident.resolution_note = data.note
        elif data.status == "reopened":
            db.scalar(select(Location).where(Location.id == incident.location_id).with_for_update())
            other = db.scalar(select(Incident).where(Incident.active_key == incident.location_id))
            if other:
                raise HTTPException(409, "Another incident is already active for this location")
            incident.active_key = incident.location_id
            incident.resolved_at = None
        old = incident.status
        incident.status = data.status
        e = TimelineEvent(
            incident_id=id,
            actor_id=user.id,
            old_status=old,
            new_status=data.status,
            note=data.note,
            evidence=evidence,
        )
        db.add(e)
        db.flush()
        audit(db, user, "incident.transition", incident, {"from": old, "to": data.status})
        notify(
            db,
            audience(db, user.campus_id),
            f"incident-status:{id}:{e.id}",
            "Network incident update",
            data.note,
        )
        return serialize(incident)

    @staticmethod
    def note(id: str, data: S.Note, user=None, db=None):
        incident = get(db, Incident, id)
        location_check(db, user, incident.location_id)
        e = TimelineEvent(
            incident_id=id, actor_id=user.id, note=data.note, visibility=data.visibility
        )
        db.add(e)
        db.flush()
        audit(db, user, "incident.note", incident)
        return serialize(e)
