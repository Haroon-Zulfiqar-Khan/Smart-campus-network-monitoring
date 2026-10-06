from datetime import timedelta
from statistics import mean, median
from sqlalchemy import select
from ..errors import DomainError as HTTPException
from .entities import (
    Threshold,
    TestAttempt,
    TestResult,
    Building,
    Location,
    Maintenance,
    Incident,
    Complaint,
    User,
    Notification,
    TimelineEvent,
    Endpoint,
    now,
)
from ..common import serialize

BANDS = [(90, "excellent"), (75, "good"), (50, "fair"), (25, "poor"), (0, "critical")]


def thresholds(db, campus_id):
    row = db.scalar(
        select(Threshold).where(Threshold.campus_id == campus_id).order_by(Threshold.version.desc())
    )
    if not row:
        raise HTTPException(503, "Campus thresholds are not configured")
    return row


def campus_for(db, location_id):
    return db.scalar(select(Building.campus_id).join(Location).where(Location.id == location_id))


def score(metrics, config):
    subs = {}
    if metrics.get("download_mbps") is not None:
        subs["download_mbps"] = min(100, metrics["download_mbps"] / config["download_target"] * 100)
    if metrics.get("upload_mbps") is not None:
        subs["upload_mbps"] = min(100, metrics["upload_mbps"] / config["upload_target"] * 100)
    if metrics.get("latency_ms") is not None:
        subs["latency_ms"] = max(
            0,
            min(
                100,
                (config["latency_bad"] - metrics["latency_ms"])
                / (config["latency_bad"] - config["latency_good"])
                * 100,
            ),
        )
    weights = config["weights"]
    coverage = sum(weights[k] for k in subs) / sum(weights.values())
    missing = [k for k in weights if k not in subs] + ["packet_loss_pct"]
    value = (
        round(sum(weights[k] * subs[k] for k in subs) / sum(weights[k] for k in subs), 2)
        if len(subs) >= 2
        else None
    )
    health = next(
        (
            name
            for minimum, name in [
                (config.get("excellent", 90), "excellent"),
                (config.get("good", 75), "good"),
                (50, "fair"),
                (25, "poor"),
                (0, "critical"),
            ]
            if value is not None and value >= minimum
        ),
        "insufficient_data",
    )
    reasons = [f"{k} below target" for k, v in subs.items() if v < 75]
    return (
        value,
        health,
        {
            "subscores": subs,
            "measurement_coverage": round(coverage, 3),
            "missing": missing,
            "reasons": reasons or ["Measured metrics meet configured targets"]
            if value is not None
            else ["At least two core metrics are required"],
            "packet_loss": "not_measured",
            "latency_method": "application RTT",
            "formula": "Weighted mean of available metric subscores; missing weights renormalized",
        },
    )


def maintenance_now(db, location_id):
    return db.scalar(
        select(Maintenance).where(
            Maintenance.location_id == location_id,
            Maintenance.cancelled.is_(False),
            Maintenance.starts_at <= now(),
            Maintenance.ends_at > now(),
        )
    )


def observed(db, location_id, since):
    return db.execute(
        select(TestAttempt, TestResult)
        .join(TestResult, TestResult.attempt_id == TestAttempt.id)
        .where(TestAttempt.location_id == location_id, TestAttempt.finished_at >= since)
        .order_by(TestAttempt.finished_at.desc())
    ).all()


def latest_per_user(rows):
    latest = {}
    for attempt, result in rows:
        if attempt.user_id not in latest:
            latest[attempt.user_id] = (attempt, result)
    return list(latest.values())


def location_health(db, location):
    config = thresholds(db, campus_for(db, location.id)).config
    rows = observed(db, location.id, now() - timedelta(minutes=config["window_minutes"]))
    independent = latest_per_user(rows)
    scored = [r.score for _, r in independent if r.score is not None]
    last = db.scalar(
        select(TestAttempt)
        .where(TestAttempt.location_id == location.id, TestAttempt.finished_at.is_not(None))
        .order_by(TestAttempt.finished_at.desc())
    )
    operational = "unknown"
    if scored:
        operational = "current" if len(scored) >= config["minimum_users"] else "low_confidence"
    elif last:
        operational = (
            "stale"
            if last.finished_at < now() - timedelta(minutes=config["stale_minutes"])
            else "insufficient_data"
        )
    active = db.scalar(select(Incident).where(Incident.active_key == location.id))
    if active:
        operational = "suspected_outage" if active.status == "suspected" else "active_incident"
    if maintenance_now(db, location.id):
        operational = "maintenance"
    aggregate = round(median(scored), 2) if scored else None
    health = next(
        (
            name
            for minimum, name in [
                (config.get("excellent", 90), "excellent"),
                (config.get("good", 75), "good"),
                (50, "fair"),
                (25, "poor"),
                (0, "critical"),
            ]
            if aggregate is not None and aggregate >= minimum
        ),
        "unknown",
    )
    stats = {}
    for k in ["download_mbps", "upload_mbps", "latency_ms"]:
        vals = [getattr(r, k) for _, r in independent if getattr(r, k) is not None]
        stats[k] = {
            "average": round(mean(vals), 2) if vals else None,
            "median": round(median(vals), 2) if vals else None,
        }
    latest_result = (
        db.scalar(select(TestResult).where(TestResult.attempt_id == last.id)) if last else None
    )
    return {
        **serialize(location),
        "operational_status": operational,
        "health": health,
        "score": aggregate,
        "sample_count": len(rows),
        "independent_users": len(independent),
        "scored_users": len(scored),
        "confidence": "sufficient" if len(scored) >= config["minimum_users"] else "low",
        "window_minutes": config["window_minutes"],
        "last_updated": serialize(last)["finished_at"] if last else None,
        "latest_result": serialize(latest_result) if latest_result else None,
        "metrics": stats,
        "incident_id": active.id if active else None,
    }


def notify(db, user_ids, key, title, message):
    for user_id in set(user_ids):
        existing = db.scalar(
            select(Notification.id).where(
                Notification.user_id == user_id, Notification.event_key == key
            )
        )
        if not existing:
            db.add(Notification(user_id=user_id, event_key=key, title=title, message=message))


def operators(db, campus_id):
    return list(
        db.scalars(
            select(User.id).where(
                User.campus_id == campus_id,
                User.is_active.is_(True),
                User.role.in_(["support", "manager", "admin"]),
            )
        )
    )


def audience(db, campus_id):
    return list(
        db.scalars(select(User.id).where(User.campus_id == campus_id, User.is_active.is_(True)))
    )


def detect_incident(db, location_id):
    # Location lock serializes detection with new submissions on PostgreSQL.
    location = db.scalar(select(Location).where(Location.id == location_id).with_for_update())
    campus = campus_for(db, location_id)
    config = thresholds(db, campus).config
    if maintenance_now(db, location_id):
        return None
    since = now() - timedelta(minutes=config["window_minutes"])
    rows = latest_per_user(observed(db, location_id, since))
    endpoints = {
        e.id
        for e in db.scalars(
            select(Endpoint).where(
                Endpoint.campus_id == campus,
                Endpoint.is_active.is_(True),
                Endpoint.operator_healthy.is_(True),
                Endpoint.last_seen_at >= now() - timedelta(minutes=10),
            )
        )
    }
    if not endpoints:
        return None
    poor = [
        (a, r)
        for a, r in rows
        if r.score is not None and r.score < config["incident_score"] and a.endpoint_id in endpoints
    ]
    complaints = list(
        db.scalars(
            select(Complaint).where(
                Complaint.location_id == location_id,
                Complaint.created_at >= since,
                Complaint.status.not_in(["resolved", "closed"]),
            )
        )
    )
    reporting = {c.user_id for c in complaints if c.category == "no_internet"}
    independent = {a.user_id for a, _ in poor} | reporting
    active = db.scalar(select(Incident).where(Incident.active_key == location_id))
    if len(independent) < config["minimum_users"] and not active:
        return None
    evidence = {
        "independent_users": len(independent),
        "test_ids": [a.id for a, _ in poor],
        "complaint_ids": [c.id for c in complaints if c.category == "no_internet"],
        "window_minutes": config["window_minutes"],
        "threshold_version": thresholds(db, campus).version,
        "endpoint_health": "operator_confirmed_with_recent_probe",
        "confidence": "suspected_crowdsourced",
    }
    if not active:
        active = Incident(location_id=location_id, active_key=location_id, evidence=evidence)
        db.add(active)
        db.flush()
        db.add(
            TimelineEvent(
                incident_id=active.id,
                new_status="suspected",
                note="Correlated reports triggered a suspected incident",
                evidence=evidence,
            )
        )
        notify(
            db,
            audience(db, campus),
            "incident:" + active.id,
            "Suspected network incident",
            f"A shared problem was reported at {location.name}. IT confirmation is pending.",
        )
    else:
        active.evidence = evidence
    for c in complaints:
        c.incident_id = active.id
    return active


def verify_recovery(db, location_id, test_ids, since, minimum_users):
    if not test_ids:
        raise HTTPException(422, "Verification tests are required")
    config = thresholds(db, campus_for(db, location_id)).config
    pairs = db.execute(
        select(TestAttempt, TestResult)
        .join(TestResult, TestResult.attempt_id == TestAttempt.id)
        .where(TestAttempt.id.in_(set(test_ids)))
    ).all()
    if len(pairs) != len(set(test_ids)):
        raise HTTPException(422, "Some verification tests do not exist")
    users = set()
    for a, r in pairs:
        if (
            a.location_id != location_id
            or a.status != "completed"
            or a.finished_at < max(since, now() - timedelta(minutes=config["window_minutes"]))
            or r.score is None
            or r.score < config["recovery_score"]
        ):
            raise HTTPException(
                422,
                "Verification must use recent complete healthy tests from the same location after the issue began",
            )
        newer = db.scalar(
            select(TestAttempt.id).where(
                TestAttempt.location_id == location_id,
                TestAttempt.user_id == a.user_id,
                TestAttempt.finished_at > a.finished_at,
                TestAttempt.status.in_(["completed", "partial", "failed"]),
            )
        )
        if newer:
            raise HTTPException(
                422,
                "Verification was superseded by a newer observation from this user; use the latest healthy test",
            )
        users.add(a.user_id)
    if len(users) < minimum_users:
        raise HTTPException(422, f"Recovery requires {minimum_users} independent users")
    return {
        "test_ids": list(set(test_ids)),
        "independent_users": len(users),
        "minimum_score": config["recovery_score"],
    }
