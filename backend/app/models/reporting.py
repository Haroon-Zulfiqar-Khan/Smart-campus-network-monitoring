from datetime import timezone
from statistics import mean
from ..errors import DomainError as HTTPException
from sqlalchemy import select
from .entities import Building, Location, TestAttempt, TestResult, Complaint, Incident
from .network import location_health

UTC = timezone.utc


def normalize_range(since, until):
    def normalized(v):
        if v is None:
            return None
        if v.tzinfo is None:
            raise HTTPException(422, "Date filters must contain UTC offset")
        return v.astimezone(UTC).replace(tzinfo=None)

    since, until = normalized(since), normalized(until)
    if since and until and since >= until:
        raise HTTPException(422, "since must precede until")
    return since, until


def collect(
    db,
    user,
    location_id=None,
    building_id=None,
    since=None,
    until=None,
    network_status=None,
    category=None,
    complaint_status=None,
):
    since, until = normalize_range(since, until)
    q = select(Location).join(Building).where(Building.campus_id == user.campus_id)
    if location_id:
        q = q.where(Location.id == location_id)
    if building_id:
        q = q.where(Location.building_id == building_id)
    locations = [
        location_health(db, location) for location in db.scalars(q.order_by(Location.name))
    ]
    if network_status:
        locations = [
            location
            for location in locations
            if location["health"] == network_status
            or location["operational_status"] == network_status
        ]
    ids = [location["id"] for location in locations]
    attempts = select(TestAttempt).where(TestAttempt.location_id.in_(ids))
    complaints = select(Complaint).where(Complaint.location_id.in_(ids))
    if since:
        attempts = attempts.where(TestAttempt.created_at >= since)
        complaints = complaints.where(Complaint.created_at >= since)
    if until:
        attempts = attempts.where(TestAttempt.created_at < until)
        complaints = complaints.where(Complaint.created_at < until)
    if category:
        complaints = complaints.where(Complaint.category == category)
    if complaint_status:
        complaints = complaints.where(Complaint.status == complaint_status)
    test_rows = list(db.scalars(attempts))
    complaint_rows = list(db.scalars(complaints))
    results = {
        r.attempt_id: r
        for r in db.scalars(
            select(TestResult).where(TestResult.attempt_id.in_([a.id for a in test_rows]))
        )
    }
    incidents = list(
        db.scalars(
            select(Incident).where(Incident.location_id.in_(ids), Incident.active_key.is_not(None))
        )
    )
    return locations, test_rows, results, complaint_rows, incidents


def average_metrics(results):
    out = {}
    for metric in ("download_mbps", "upload_mbps", "latency_ms", "score"):
        vals = [getattr(r, metric) for r in results if getattr(r, metric) is not None]
        out["average_" + metric] = round(mean(vals), 2) if vals else None
    return out
