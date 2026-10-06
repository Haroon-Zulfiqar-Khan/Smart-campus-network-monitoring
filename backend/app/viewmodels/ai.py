"""Administrator AI use cases; campus-scoped facts, audit history and explicit review."""

from collections import Counter, defaultdict
from datetime import timedelta, timezone
from statistics import mean
from zoneinfo import ZoneInfo
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import select
from ..models import (
    Complaint,
    Location,
    Building,
    User,
    Audit,
    TestAttempt,
    TestResult,
    Campus,
    now,
)
from ..models import gemini
from ..config import settings
from ..common import get, complaint_access, audit, serialize
from ..errors import DomainError


class BatchInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    limit: int = Field(default=1, ge=1, le=1)


def require_admin(user):
    if user.role != "admin":
        raise DomainError(403, "Administrator access is required for AI insights.")


def classify_complaint(db, user, complaint, automatic=False):
    result = gemini.classify(complaint.description)
    original = complaint.category
    applied = automatic and result["method"] == "gemini" and result["confidence"] >= 0.65
    if applied:
        complaint.category = result["category"]
    details = {**result, "original_category": original, "applied": applied}
    audit(db, user, "ai.complaint_classified", complaint, details)
    db.flush()
    return details


def listing(user=None, db=None):
    require_admin(user)
    complaints = list(
        db.scalars(
            select(Complaint)
            .join(Location)
            .join(Building)
            .where(Building.campus_id == user.campus_id)
            .order_by(Complaint.created_at.desc())
            .limit(200)
        )
    )
    analyses = {}
    for row in db.scalars(
        select(Audit)
        .where(
            Audit.action == "ai.complaint_classified",
            Audit.entity_id.in_([c.id for c in complaints]),
        )
        .order_by(Audit.created_at.desc())
    ):
        if row.entity_id not in analyses:
            analyses[row.entity_id] = {**row.details, "analyzed_at": serialize(row)["created_at"]}
    report = db.scalar(
        select(Audit)
        .join(User, User.id == Audit.actor_id)
        .where(User.campus_id == user.campus_id, Audit.action == "ai.network_summary_generated")
        .order_by(Audit.created_at.desc())
    )
    return {
        "configured": bool(settings.gemini_api_key.get_secret_value()),
        "model": settings.gemini_model,
        "complaints": [
            {
                "id": c.id,
                "reference": c.reference,
                "description": c.description,
                "category": c.category,
                "location": db.get(Location, c.location_id).name,
                "analysis": analyses.get(c.id),
            }
            for c in complaints
        ],
        "last_summary": report.details if report else None,
    }


def classify_one(id, user=None, db=None):
    require_admin(user)
    complaint = get(db, Complaint, id)
    complaint_access(db, user, complaint)
    return classify_complaint(db, user, complaint)


def batch(data, user=None, db=None):
    require_admin(user)
    analyzed = select(Audit.entity_id).where(Audit.action == "ai.complaint_classified")
    complaints = list(
        db.scalars(
            select(Complaint)
            .join(Location)
            .join(Building)
            .where(Building.campus_id == user.campus_id, Complaint.id.not_in(analyzed))
            .order_by(Complaint.created_at.desc())
            .limit(data.limit)
        )
    )
    return {
        "processed": len(complaints),
        "results": [classify_complaint(db, user, c) for c in complaints],
    }


def apply(id, user=None, db=None):
    require_admin(user)
    complaint = get(db, Complaint, id)
    complaint_access(db, user, complaint)
    record = db.scalar(
        select(Audit)
        .where(Audit.entity_id == id, Audit.action == "ai.complaint_classified")
        .order_by(Audit.created_at.desc())
    )
    if not record:
        raise DomainError(409, "Classify this complaint before applying a category.")
    original = complaint.category
    complaint.category = record.details["category"]
    from .complaints import event

    event(
        db,
        user,
        complaint,
        complaint.status,
        complaint.status,
        "Complaint category reviewed and updated by the administrator.",
    )
    audit(
        db,
        user,
        "ai.classification_applied",
        complaint,
        {"previous": original, "category": complaint.category},
    )
    record.details = {**record.details, "applied": True}
    return {"category": complaint.category}


def summary(hours: int = 72, user=None, db=None):
    require_admin(user)
    if hours not in (24, 72, 168):
        raise DomainError(422, "Choose the last 24 hours, 3 days or 7 days.")
    latest = db.scalar(
        select(Audit)
        .join(User, User.id == Audit.actor_id)
        .where(
            User.campus_id == user.campus_id,
            Audit.action == "ai.network_summary_generated",
            Audit.created_at >= now() - timedelta(seconds=30),
        )
    )
    if latest:
        raise DomainError(
            429,
            "A summary was generated recently. Please wait 30 seconds before generating another.",
        )
    start = now() - timedelta(hours=hours)
    locations = list(
        db.scalars(select(Location).join(Building).where(Building.campus_id == user.campus_id))
    )
    ids = [location.id for location in locations]
    tests = list(
        db.execute(
            select(TestAttempt, TestResult)
            .join(TestResult, TestResult.attempt_id == TestAttempt.id)
            .where(TestAttempt.location_id.in_(ids), TestAttempt.created_at >= start)
        )
    )
    complaints = list(
        db.scalars(
            select(Complaint).where(Complaint.location_id.in_(ids), Complaint.created_at >= start)
        )
    )
    timezone_name = db.get(Campus, user.campus_id).timezone
    tz = ZoneInfo(timezone_name)
    groups = defaultdict(list)
    for attempt, result in tests:
        groups[attempt.location_id].append((attempt, result))

    def average(rows, field):
        values = [getattr(r, field) for _, r in rows if getattr(r, field) is not None]
        return round(mean(values), 1) if values else None

    areas = []
    for location in locations:
        rows = groups[location.id]
        own = [c for c in complaints if c.location_id == location.id]
        if not rows and not own:
            continue
        hourly = defaultdict(list)
        for attempt, result in rows:
            hour = (
                attempt.created_at.replace(tzinfo=timezone.utc)
                .astimezone(tz)
                .strftime("%Y-%m-%d %H:00")
            )
            hourly[hour].append((attempt, result))
        areas.append(
            {
                "location": location.name,
                "building": db.get(Building, location.building_id).name,
                "tests": len(rows),
                "independent_users": len({a.user_id for a, r in rows}),
                "avg_download_mbps": average(rows, "download_mbps"),
                "avg_upload_mbps": average(rows, "upload_mbps"),
                "avg_latency_ms": average(rows, "latency_ms"),
                "complaints": len(own),
                "open_complaints": sum(c.status not in ("resolved", "closed") for c in own),
                "reported_categories": dict(Counter(c.category for c in own)),
                "hourly_observations": [
                    {
                        "hour": h,
                        "samples": len(items),
                        "download_mbps": average(items, "download_mbps"),
                        "latency_ms": average(items, "latency_ms"),
                    }
                    for h, items in sorted(hourly.items())
                ][-24:],
            }
        )
    # Bound context while preserving exact whole-campus totals.
    areas.sort(key=lambda a: (a["open_complaints"], a["tests"]), reverse=True)
    facts = {
        "hours": hours,
        "timezone": timezone_name,
        "test_count": len(tests),
        "complaint_count": len(complaints),
        "locations_with_data": len(areas),
        "shown_locations": areas[:20],
        "hourly_coverage": "Latest 24 nonempty hourly buckets per shown location; totals cover the entire selected period.",
        "omitted_locations": max(0, len(areas) - 20),
        "category_counts": dict(Counter(c.category for c in complaints)),
    }
    if not tests and not complaints:
        result = {
            "summary": "No tests or complaints were recorded in this period. There is not enough evidence to assess network health.",
            "observations": [],
            "recommendations": [
                "Collect connection tests from campus locations before drawing conclusions."
            ],
            "limitations": ["No recorded evidence is available for the selected period."],
        }
        method = "data_summary"
        warning = None
    else:
        try:
            result = gemini.generate(
                "Write a concise, plain-English IT network summary using only these computed campus facts. "
                "Identify recurring symptoms and affected locations. Mention time patterns only when the hourly observations support them. "
                "Do not infer peak usage, root cause, outage confirmation or Wi-Fi signal from HTTP speed tests. "
                "Separate observations from suggested checks. Mention sparse samples and omitted locations. "
                "Use at most 5 observations and 4 practical recommendations.",
                facts,
                gemini.Insight,
            ).model_dump()
            method = "gemini"
            warning = None
        except gemini.GeminiUnavailable as error:
            result = {
                "summary": f"The last {hours} hours contain {len(tests)} saved tests and {len(complaints)} complaints across {len(areas)} locations.",
                "observations": [
                    f"{area['location']}: {area['tests']} tests and {area['open_complaints']} open complaints."
                    for area in areas[:5]
                ],
                "recommendations": [
                    "Review locations with repeated reports and compare multiple users’ measurements."
                ],
                "limitations": [
                    "This is a factual data summary; Gemini did not generate insights."
                ],
            }
            method = "data_summary"
            warning = str(error)
    output = {
        **result,
        "method": method,
        "model": settings.gemini_model if method == "gemini" else None,
        "warning": warning,
        "hours": hours,
        "generated_at": now().isoformat() + "Z",
        "facts": facts,
    }
    audit(db, user, "ai.network_summary_generated", db.get(Campus, user.campus_id), output)
    return output


class AIViewModel:
    listing = staticmethod(listing)
    classify_one = staticmethod(classify_one)
    batch = staticmethod(batch)
    apply = staticmethod(apply)
    summary = staticmethod(summary)
