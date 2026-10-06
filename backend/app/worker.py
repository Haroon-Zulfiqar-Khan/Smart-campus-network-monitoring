"""Periodic deterministic rules, expiry and maintenance-end notifications."""

import logging
import time
from sqlalchemy import select
from .config import settings
from .db import SessionLocal
from .models import Location, TestAttempt, Maintenance, now
from .services import detect_incident, notify, audience, campus_for


def tick(db):
    for a in db.scalars(
        select(TestAttempt).where(
            TestAttempt.expires_at < now(), TestAttempt.status.in_(["created", "running"])
        )
    ):
        a.status = "failed"
        a.reason = "Session expired without a saved outcome"
        a.finished_at = now()
    for location in db.scalars(select(Location).where(Location.is_active.is_(True))):
        detect_incident(db, location.id)
    for m in db.scalars(
        select(Maintenance).where(Maintenance.ends_at <= now(), Maintenance.cancelled.is_(False))
    ):
        notify(
            db,
            audience(db, campus_for(db, m.location_id)),
            "maintenance-ended:" + m.id,
            "Maintenance window ended",
            "The scheduled window ended. Network recovery still requires measurements.",
        )


def main():
    logging.basicConfig(level=logging.INFO)
    while True:
        try:
            with SessionLocal() as db:
                tick(db)
                db.commit()
        except Exception as exc:
            logging.error("Worker tick failed (%s)", type(exc).__name__)
        time.sleep(settings.worker_interval_seconds)


if __name__ == "__main__":
    main()
