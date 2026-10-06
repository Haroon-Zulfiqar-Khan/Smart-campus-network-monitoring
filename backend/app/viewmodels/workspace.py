"""Authenticated presentation adapter; retains the domain API and its transition rules."""

from pydantic import BaseModel, Field, ConfigDict, model_validator
from sqlalchemy import select
from ..models import (
    Building,
    Location,
    User,
    Complaint,
    TimelineEvent,
    TestAttempt,
    TestResult,
    Notification,
)
from ..models.extensions import RolePolicy, MaintenanceNote, DEFAULTS, allowed
from ..models.network import location_health, thresholds, notify, operators
from ..common import serialize, audit, location_check
from ..errors import DomainError

ROLES = {
    "student": "Student",
    "staff": "Student",
    "support": "IT Support",
    "manager": "Manager",
    "admin": "Administrator",
}
STATUS = {
    "submitted": "Open",
    "reviewed": "Open",
    "assigned": "Assigned",
    "in_progress": "In Progress",
    "awaiting_user": "In Progress",
    "awaiting_external": "In Progress",
    "reopened": "In Progress",
    "resolved": "Resolved",
    "closed": "Resolved",
}
CATEGORIES = {
    "no_internet": "No Internet",
    "slow_internet": "Slow Internet",
    "high_ping": "High Latency",
    "frequent_disconnection": "Disconnections",
    "weak_signal": "Weak Signal",
    "service_unavailable": "Website / Service Unavailable",
    "other": "Other",
}


def require(db, user, cap):
    if not allowed(db, user, cap):
        raise DomainError(403, "Your account does not have permission to perform this action.")


def test_row(a, r):
    return {
        "id": a.id,
        "locationId": a.location_id,
        "download": r.download_mbps,
        "upload": r.upload_mbps,
        "ping": r.latency_ms,
        "score": r.score,
        "health": r.health,
        "testedAt": serialize(a)["finished_at"] or serialize(a)["created_at"],
        "simulated": False,
        "owner": a.user_id,
        "outcome": a.status,
    }


def snapshot(user=None, db=None):
    buildings = list(db.scalars(select(Building).where(Building.campus_id == user.campus_id)))
    names = {b.id: b.name for b in buildings}
    locations = list(
        db.scalars(
            select(Location).where(Location.building_id.in_(names), Location.is_active.is_(True))
        )
    )
    ids = [location.id for location in locations]
    people = list(db.scalars(select(User).where(User.campus_id == user.campus_id)))
    users = {u.id: u.name for u in people}
    cs = list(
        db.scalars(
            select(Complaint)
            .where(
                Complaint.location_id.in_(ids),
                *(
                    []
                    if user.role in ("support", "manager", "admin")
                    and (
                        user.role == "admin"
                        or allowed(db, user, "complaints")
                        or allowed(db, user, "reports")
                    )
                    else [Complaint.user_id == user.id]
                ),
            )
            .order_by(Complaint.created_at.desc())
        )
    )
    events = list(
        db.scalars(
            select(TimelineEvent)
            .where(TimelineEvent.complaint_id.in_([c.id for c in cs]))
            .order_by(TimelineEvent.created_at)
        )
    )
    visible_events = [
        e
        for e in events
        if e.visibility == "public" or user.role in ("support", "manager", "admin")
    ]
    history = []
    tests = []
    for a, r in db.execute(
        select(TestAttempt, TestResult)
        .join(TestResult, TestResult.attempt_id == TestAttempt.id)
        .where(TestAttempt.location_id.in_(ids))
        .order_by(TestAttempt.created_at.desc())
    ):
        row = test_row(a, r)
        history.append({k: v for k, v in row.items() if k != "owner"})
        if (
            a.user_id == user.id
            or user.role == "admin"
            or (user.role == "support" and allowed(db, user, "tests"))
            or (user.role == "manager" and allowed(db, user, "reports"))
        ):
            tests.append(row)
    config = thresholds(db, user.campus_id).config
    notifications = list(
        db.scalars(
            select(Notification)
            .where(Notification.user_id == user.id)
            .order_by(Notification.created_at.desc())
            .limit(200)
        )
    )
    notes = (
        list(
            db.scalars(
                select(MaintenanceNote)
                .where(MaintenanceNote.location_id.in_(ids))
                .order_by(MaintenanceNote.created_at.desc())
            )
        )
        if user.role == "admin" or allowed(db, user, "maintenance") or allowed(db, user, "reports")
        else []
    )
    policies = {ROLES[r]: list(DEFAULTS[r]) for r in ("student", "support", "manager", "admin")}
    for row in db.scalars(select(RolePolicy).where(RolePolicy.campus_id == user.campus_id)):
        policies[ROLES[row.role]] = row.permissions
    role = ROLES[user.role]
    return {
        "user": serialize(user),
        "locations": [
            {
                "id": location.id,
                "name": location.name,
                "building": names[location.building_id],
                "floor": location.floor,
                "latitude": location.latitude,
                "longitude": location.longitude,
                "coordinateSource": "manual" if location.latitude is not None else None,
                "userReported": location.user_reported,
                "score": (h := location_health(db, location))["score"],
                "download": h["metrics"]["download_mbps"]["average"],
                "upload": h["metrics"]["upload_mbps"]["average"],
                "ping": h["metrics"]["latency_ms"]["average"],
                "tests": h["scored_users"],
                "x": 0,
                "y": 0,
            }
            for location in locations
        ],
        "tests": tests,
        "networkHistory": history,
        "complaints": [
            {
                "id": c.id,
                "reference": c.reference,
                "locationId": c.location_id,
                "category": CATEGORIES[c.category],
                "description": c.description,
                "status": STATUS.get(c.status, "Open"),
                "rawStatus": c.status,
                "assigneeId": c.assignee_id,
                "assignee": users.get(c.assignee_id, "Unassigned"),
                "createdAt": serialize(c)["created_at"],
                "owner": c.user_id,
                "testId": c.test_id,
                "attachedTest": attached_test(db, c.test_id, history),
                "notes": [e.note for e in visible_events if e.complaint_id == c.id],
            }
            for c in cs
        ],
        "users": [
            {"id": u.id, "name": u.name, "role": ROLES[u.role], "active": u.is_active}
            for u in people
            if user.role == "admin"
            or (user.role in ("support", "manager") and u.role in ("support", "manager", "admin"))
        ],
        "thresholds": {"good": config.get("good", 75), "excellent": config.get("excellent", 90)},
        "permissions": policies,
        "maintenanceNotes": [
            {
                "id": n.id,
                "locationId": n.location_id,
                "text": n.text,
                "author": users.get(n.author_id, "IT Support"),
                "createdAt": serialize(n)["created_at"],
            }
            for n in notes
        ],
        "supportActivities": [
            {
                "id": e.id,
                "locationId": next(c.location_id for c in cs if c.id == e.complaint_id),
                "complaintId": e.complaint_id,
                "status": STATUS.get(e.new_status, "Open"),
                "assignee": users.get(e.actor_id, "IT Support"),
                "actor": users.get(e.actor_id, "IT Support"),
                "note": e.note,
                "createdAt": serialize(e)["created_at"],
            }
            for e in visible_events
        ]
        if user.role in ("manager", "admin", "support")
        else [],
        "alerts": [
            {
                "id": n.id,
                "message": n.title + ": " + n.message,
                "kind": "info",
                "createdAt": serialize(n)["created_at"],
                "recipients": [role],
                "readBy": [role] if n.is_read else [],
            }
            for n in notifications
        ],
    }


def attached_test(db, test_id, history):
    if not test_id:
        return None
    existing = next((row for row in history if row["id"] == test_id), None)
    if existing:
        return existing
    attempt = db.get(TestAttempt, test_id)
    if not attempt:
        return None
    return {
        "id": attempt.id,
        "locationId": attempt.location_id,
        "download": None,
        "upload": None,
        "ping": None,
        "score": None,
        "testedAt": serialize(attempt)["finished_at"] or serialize(attempt)["created_at"],
        "outcome": attempt.status,
        "simulated": False,
    }


class LocationInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, allow_inf_nan=False)
    name: str = Field(min_length=2, max_length=80)
    building: str = Field(default="Custom locations", min_length=2, max_length=80)
    floor: str = Field(default="User-reported location", max_length=40)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)

    @model_validator(mode="after")
    def coordinates(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("Supply both latitude and longitude.")
        return self


def building_for(db, user, name):
    b = db.scalar(
        select(Building).where(Building.campus_id == user.campus_id, Building.name == name)
    )
    if not b:
        b = Building(campus_id=user.campus_id, name=name)
        db.add(b)
        db.flush()
    return b


def create_location(data: LocationInput, user=None, db=None):
    custom = user.role != "admin"
    if custom and (data.latitude is None or data.longitude is None):
        raise DomainError(422, "Select a map position for your custom location.")
    b = building_for(db, user, "Custom locations" if custom else data.building)
    location = Location(
        building_id=b.id,
        name=data.name.strip(),
        floor=data.floor.strip(),
        latitude=data.latitude,
        longitude=data.longitude,
        user_reported=custom,
    )
    db.add(location)
    db.flush()
    audit(db, user, "location.created", location)
    notify(db, [user.id], f"location:{location.id}", "Location saved", location.name)
    return serialize(location)


def edit_location(id: str, data: LocationInput, user=None, db=None):
    if user.role != "admin":
        raise DomainError(403, "Administrator access is required.")
    location = location_check(db, user, id)
    location.building_id = building_for(db, user, data.building).id
    for k in ("name", "floor", "latitude", "longitude"):
        setattr(location, k, getattr(data, k))
    audit(db, user, "location.updated", location)
    notify(
        db,
        [user.id],
        f"location-edit:{location.id}:{__import__('uuid').uuid4()}",
        "Location updated",
        location.name,
    )
    return serialize(location)


class NoteInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    location_id: str
    text: str = Field(min_length=10, max_length=1000)


def maintenance_note(data: NoteInput, user=None, db=None):
    require(db, user, "maintenance")
    location_check(db, user, data.location_id)
    if len(data.text.strip()) < 10:
        raise DomainError(422, "Enter a maintenance note of at least 10 characters.")
    n = MaintenanceNote(location_id=data.location_id, author_id=user.id, text=data.text.strip())
    db.add(n)
    db.flush()
    audit(db, user, "maintenance.note_added", n)
    notify(
        db,
        operators(db, user.campus_id),
        f"maintenance-note:{n.id}",
        "Maintenance note added",
        n.text,
    )
    return serialize(n)


class PolicyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    permissions: list[str]


def policy(role: str, data: PolicyInput, user=None, db=None):
    if user.role != "admin":
        raise DomainError(403, "Administrator access is required.")
    valid = {"support": {"tests", "complaints", "maintenance", "reports"}, "manager": {"reports"}}
    if role not in valid or not set(data.permissions) <= valid[role]:
        raise DomainError(422, "Invalid role capabilities.")
    row = db.scalar(
        select(RolePolicy).where(RolePolicy.campus_id == user.campus_id, RolePolicy.role == role)
    )
    if not row:
        row = RolePolicy(campus_id=user.campus_id, role=role, permissions=[])
        db.add(row)
    row.permissions = sorted(set(data.permissions))
    db.flush()
    audit(db, user, "permissions.updated", row)
    return serialize(row)


def staff(user=None, db=None):
    if user.role not in ("support", "manager", "admin"):
        raise DomainError(403, "IT access is required.")
    return [
        serialize(u)
        for u in db.scalars(
            select(User).where(
                User.campus_id == user.campus_id,
                User.is_active.is_(True),
                User.role.in_(["support", "manager", "admin"]),
            )
        )
    ]


class WorkspaceViewModel:
    snapshot = staticmethod(snapshot)
    create_location = staticmethod(create_location)
    edit_location = staticmethod(edit_location)
    maintenance_note = staticmethod(maintenance_note)
    policy = staticmethod(policy)
    staff = staticmethod(staff)


class ComplaintUpdateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str
    assignee_id: str | None = None
    note: str = Field(default="", max_length=2000)


def update_complaint(id, data, user=None, db=None):
    from ..viewmodels.complaints import ComplaintsViewModel
    from ..schemas import ComplaintTransition as Transition, Assignment, Note
    from ..common import get, complaint_access

    require(db, user, "complaints")
    c = get(db, Complaint, id)
    complaint_access(db, user, c)
    if data.status not in ("Open", "Assigned", "In Progress", "Resolved"):
        raise DomainError(422, "Invalid complaint status.")
    vm = ComplaintsViewModel()
    if data.status == "Resolved":
        from ..common import support_check

        if data.assignee_id:
            c.assignee_id = support_check(db, user, data.assignee_id).id
        return vm.transition(
            id=id,
            data=Transition(
                status="resolved", note=data.note.strip() or "Marked resolved by IT support."
            ),
            user=user,
            db=db,
        )
    if data.status != "Open" and not (data.assignee_id or c.assignee_id):
        raise DomainError(422, "Select an IT staff member before assignment.")
    if c.status == "submitted" and data.status != "Open":
        vm.transition(
            id=id, data=Transition(status="reviewed", note="Reviewed by IT"), user=user, db=db
        )
    if data.assignee_id and data.assignee_id != c.assignee_id:
        vm.assign(
            id=id,
            data=Assignment(assignee_id=data.assignee_id, note="Assigned by IT"),
            user=user,
            db=db,
        )
    if data.status in ("In Progress", "Resolved") and c.status == "assigned":
        vm.transition(
            id=id,
            data=Transition(status="in_progress", note="Investigation started"),
            user=user,
            db=db,
        )
    if data.note.strip():
        vm.note(id=id, data=Note(note=data.note, visibility="public"), user=user, db=db)
    return serialize(c)


WorkspaceViewModel.update_complaint = staticmethod(update_complaint)


class InternetTestInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    location_id: str
    submission_id: str = Field(min_length=8, max_length=100)


def internet_test(data, user=None, db=None):
    from ..models import Endpoint
    from ..schemas import StartTest
    from .tests import TestsViewModel

    location_check(db, user, data.location_id, active=True)
    endpoint = db.scalar(
        select(Endpoint).where(
            Endpoint.campus_id == user.campus_id,
            Endpoint.scope == "internet",
            Endpoint.base_url == "https://speed.cloudflare.com",
            Endpoint.is_active.is_(True),
        )
    )
    if not endpoint:
        endpoint = Endpoint(
            campus_id=user.campus_id,
            name="Cloudflare Internet Speed Test",
            base_url="https://speed.cloudflare.com",
            scope="internet",
        )
        db.add(endpoint)
        db.flush()
    response = TestsViewModel.start(
        data=StartTest(
            location_id=data.location_id,
            endpoint_id=endpoint.id,
            submission_id=data.submission_id,
            campus_wifi_confirmed=False,
        ),
        user=user,
        db=db,
    )
    response["transport"] = "cloudflare"
    response["notice"] = (
        "Measures this device’s active internet connection to Cloudflare. Wi-Fi signal and packet loss are not measured."
    )
    return response


WorkspaceViewModel.internet_test = staticmethod(internet_test)
