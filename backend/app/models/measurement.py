"""Model: authorization and atomic measurement counters."""

from sqlalchemy import update
from ..db import SessionLocal
from ..config import settings
from ..errors import DomainError
from ..security import decode
from .entities import TestAttempt, Endpoint, User, now


def authorize(token, db):
    claims = decode(token, "campus-measurement")
    attempt = db.get(TestAttempt, claims.get("sid"))
    user = db.get(User, claims["sub"])
    if (
        not attempt
        or attempt.user_id != claims["sub"]
        or attempt.endpoint_id != claims.get("eid")
        or attempt.expires_at <= now()
        or attempt.status not in ("created", "running")
    ):
        raise DomainError(409, "Measurement session is not active")
    endpoint = db.get(Endpoint, attempt.endpoint_id)
    if not endpoint or not endpoint.is_active or not user or not user.is_active:
        raise DomainError(403, "Measurement access disabled")
    endpoint.last_seen_at = now()
    db.commit()
    return attempt.id


def reserve(id, size):
    with SessionLocal() as db:
        result = db.execute(
            update(TestAttempt)
            .where(
                TestAttempt.id == id,
                TestAttempt.status.in_(["created", "running"]),
                TestAttempt.expires_at > now(),
                TestAttempt.transfer_bytes + size <= settings.max_session_bytes,
            )
            .values(transfer_bytes=TestAttempt.transfer_bytes + size, status="running")
        )
        if result.rowcount != 1:
            raise DomainError(429, "Session byte budget exhausted or session finalized")
        db.commit()


def confirm_upload(id, received):
    with SessionLocal() as db:
        db.execute(
            update(TestAttempt)
            .where(TestAttempt.id == id)
            .values(upload_confirmed_bytes=TestAttempt.upload_confirmed_bytes + received)
        )
        db.commit()
