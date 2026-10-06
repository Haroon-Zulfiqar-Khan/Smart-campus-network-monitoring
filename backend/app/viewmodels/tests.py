from datetime import timedelta, datetime
import jwt
from ..errors import DomainError as HTTPException
from sqlalchemy import select, func
from .. import schemas as S
from ..models import TestAttempt, TestResult, Endpoint, Building, Location, now
from ..config import settings
from ..common import get, location_check, campus_check, serialize, audit, OPS
from ..models.network import thresholds, score, detect_incident, notify, operators


def session_response(attempt, endpoint):
    token = jwt.encode(
        {
            "sub": attempt.user_id,
            "sid": attempt.id,
            "eid": endpoint.id,
            "aud": "campus-measurement",
            "exp": attempt.expires_at,
        },
        settings.secret_key,
        algorithm="HS256",
    )
    return {
        **serialize(attempt),
        "measurement_token": token,
        "base_url": endpoint.base_url,
        "limits": {
            "download_bytes": settings.max_download_bytes,
            "upload_bytes": settings.max_upload_bytes,
            "session_bytes": settings.max_session_bytes,
        },
        "notice": "Measures this device to the selected endpoint. Location and metrics are user-reported. HTTP latency is application RTT; packet loss is not measured.",
    }


class TestsViewModel:
    """Orchestrates use cases and prepares state consumed by API Views."""

    @staticmethod
    def start(data: S.StartTest, user=None, db=None):
        location_check(db, user, data.location_id, active=True)
        endpoint = get(db, Endpoint, data.endpoint_id)
        campus_check(user, endpoint.campus_id)
        if not endpoint.is_active:
            raise HTTPException(409, "Endpoint disabled")
        old = db.scalar(
            select(TestAttempt).where(
                TestAttempt.user_id == user.id, TestAttempt.submission_id == data.submission_id
            )
        )
        if old:
            if old.location_id != data.location_id or old.endpoint_id != data.endpoint_id:
                raise HTTPException(409, "Submission ID already used for a different test")
            return session_response(old, endpoint)
        active = db.scalar(
            select(func.count())
            .select_from(TestAttempt)
            .where(
                TestAttempt.user_id == user.id,
                TestAttempt.status.in_(["created", "running"]),
                TestAttempt.expires_at > now(),
            )
        )
        if active >= 2:
            raise HTTPException(429, "Finish or cancel an active test before starting another")
        attempt = TestAttempt(
            user_id=user.id,
            location_id=data.location_id,
            endpoint_id=data.endpoint_id,
            submission_id=data.submission_id,
            expires_at=now() + timedelta(minutes=settings.test_session_minutes),
        )
        db.add(attempt)
        db.flush()
        return session_response(attempt, endpoint)

    @staticmethod
    def result(id: str, data: S.TestOutcome, user=None, db=None):
        attempt = db.scalar(select(TestAttempt).where(TestAttempt.id == id).with_for_update())
        if not attempt:
            raise HTTPException(404, "Test session not found")
        if attempt.user_id != user.id:
            raise HTTPException(403, "Test belongs to another user")
        previous = db.scalar(select(TestResult).where(TestResult.attempt_id == id))
        if attempt.status in ("completed", "partial", "failed", "cancelled"):
            same = attempt.status == data.status and attempt.reason == data.reason
            if previous:
                same = same and all(
                    (
                        getattr(previous, k) == getattr(data, k)
                        for k in ("download_mbps", "upload_mbps", "latency_ms", "jitter_ms")
                    )
                )
            elif any(
                (
                    getattr(data, k) is not None
                    for k in ("download_mbps", "upload_mbps", "latency_ms", "jitter_ms")
                )
            ):
                same = False
            if not same:
                raise HTTPException(409, "Session already finalized with a different outcome")
            return {
                "attempt": serialize(attempt),
                "result": serialize(previous) if previous else None,
                "duplicate": True,
            }
        if attempt.expires_at < now():
            raise HTTPException(409, "Test session expired")
        endpoint = get(db, Endpoint, attempt.endpoint_id)
        external = (
            endpoint.scope == "internet" and endpoint.base_url == "https://speed.cloudflare.com"
        )
        if data.upload_mbps is not None and attempt.upload_confirmed_bytes == 0 and not external:
            raise HTTPException(
                422, "Upload requires server-confirmed bytes from the measurement endpoint"
            )
        attempt.status = data.status
        attempt.finished_at = now()
        attempt.reason = data.reason
        saved = None
        if data.status in ("completed", "partial"):
            threshold = thresholds(db, user.campus_id)
            metrics = data.model_dump(exclude={"status", "reason"})
            value, health, explanation = score(metrics, threshold.config)
            saved = TestResult(
                attempt_id=attempt.id,
                **metrics,
                score=value,
                health=health,
                explanation=explanation,
                threshold_version=threshold.version,
            )
            db.add(saved)
            db.flush()
            if health in ("poor", "critical"):
                key = f"poor:{attempt.location_id}:{now().strftime('%Y%m%d%H')}"
                notify(
                    db,
                    operators(db, user.campus_id),
                    key,
                    "Poor network observation",
                    "A recent device test reported poor network performance; investigate before confirming an outage.",
                )
        audit(db, user, "test.finalized", attempt, {"status": data.status})
        db.flush()
        detect_incident(db, attempt.location_id)
        return {
            "attempt": serialize(attempt),
            "result": serialize(saved) if saved else None,
            "duplicate": False,
        }

    @staticmethod
    def history(
        location_id: str | None = None,
        building_id: str | None = None,
        status: str | None = None,
        health: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        mine: bool = True,
        limit: int = 50,
        offset: int = 0,
        user=None,
        db=None,
    ):
        from ..models.reporting import normalize_range

        since, until = normalize_range(since, until)
        q = (
            select(TestAttempt)
            .join(Location)
            .join(Building)
            .where(Building.campus_id == user.campus_id)
        )
        if mine or user.role not in OPS:
            q = q.where(TestAttempt.user_id == user.id)
        if location_id:
            q = q.where(TestAttempt.location_id == location_id)
        if building_id:
            q = q.where(Location.building_id == building_id)
        if status:
            q = q.where(TestAttempt.status == status)
        if since:
            q = q.where(TestAttempt.created_at >= since)
        if until:
            q = q.where(TestAttempt.created_at < until)
        if health:
            q = q.join(TestResult).where(TestResult.health == health)
        total = db.scalar(select(func.count()).select_from(q.subquery()))
        rows = list(
            db.scalars(q.order_by(TestAttempt.created_at.desc()).limit(limit).offset(offset))
        )
        return {
            "items": [
                {
                    "attempt": serialize(a),
                    "result": serialize(r)
                    if (r := db.scalar(select(TestResult).where(TestResult.attempt_id == a.id)))
                    else None,
                }
                for a in rows
            ],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    @staticmethod
    def test(id: str, user=None, db=None):
        a = get(db, TestAttempt, id)
        location_check(db, user, a.location_id)
        if user.role not in OPS and a.user_id != user.id:
            raise HTTPException(403, "Test belongs to another user")
        r = db.scalar(select(TestResult).where(TestResult.attempt_id == id))
        e = get(db, Endpoint, a.endpoint_id)
        return {
            "attempt": serialize(a),
            "result": serialize(r) if r else None,
            "endpoint": serialize(e),
        }
