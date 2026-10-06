from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import (
    String,
    Text,
    Float,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    JSON,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from ..db import Base


def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def uid():
    return str(uuid4())


class Record:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, index=True)


class Campus(Record, Base):
    __tablename__ = "campuses"
    name: Mapped[str] = mapped_column(String(120))
    timezone: Mapped[str] = mapped_column(String(60), default="Asia/Karachi")


class User(Record, Base):
    __tablename__ = "users"
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(20), default="student")
    campus_id: Mapped[str] = mapped_column(ForeignKey("campuses.id"), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class LoginSession(Record, Base):
    __tablename__ = "login_sessions"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    refresh_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)


class Building(Record, Base):
    __tablename__ = "buildings"
    campus_id: Mapped[str] = mapped_column(ForeignKey("campuses.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    __table_args__ = (UniqueConstraint("campus_id", "name"),)


class Location(Record, Base):
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    user_reported: Mapped[bool] = mapped_column(Boolean, default=False)
    __tablename__ = "locations"
    building_id: Mapped[str] = mapped_column(ForeignKey("buildings.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    floor: Mapped[str] = mapped_column(String(40), default="Ground")
    description: Mapped[str] = mapped_column(Text, default="")
    map_x: Mapped[float | None] = mapped_column(Float, nullable=True)
    map_y: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (UniqueConstraint("building_id", "floor", "name"),)


class Endpoint(Record, Base):
    __tablename__ = "endpoints"
    campus_id: Mapped[str] = mapped_column(ForeignKey("campuses.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    base_url: Mapped[str] = mapped_column(String(500))
    scope: Mapped[str] = mapped_column(String(20), default="campus")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    operator_healthy: Mapped[bool] = mapped_column(Boolean, default=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Threshold(Record, Base):
    __tablename__ = "thresholds"
    campus_id: Mapped[str] = mapped_column(ForeignKey("campuses.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    config: Mapped[dict] = mapped_column(JSON)
    __table_args__ = (UniqueConstraint("campus_id", "version"),)


class TestAttempt(Record, Base):
    __tablename__ = "test_attempts"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    location_id: Mapped[str] = mapped_column(ForeignKey("locations.id"), index=True)
    endpoint_id: Mapped[str] = mapped_column(ForeignKey("endpoints.id"))
    submission_id: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20), default="created")
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    transfer_bytes: Mapped[int] = mapped_column(Integer, default=0)
    upload_confirmed_bytes: Mapped[int] = mapped_column(Integer, default=0)
    __table_args__ = (UniqueConstraint("user_id", "submission_id"),)


class TestResult(Record, Base):
    __tablename__ = "test_results"
    attempt_id: Mapped[str] = mapped_column(ForeignKey("test_attempts.id"), unique=True)
    download_mbps: Mapped[float | None] = mapped_column(Float, nullable=True)
    upload_mbps: Mapped[float | None] = mapped_column(Float, nullable=True)
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    jitter_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    packet_loss_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    health: Mapped[str] = mapped_column(String(30))
    explanation: Mapped[dict] = mapped_column(JSON)
    threshold_version: Mapped[int] = mapped_column(Integer)
    measurement_method: Mapped[str] = mapped_column(
        String(100), default="browser_http_application_rtt"
    )
    trust: Mapped[str] = mapped_column(String(50), default="client_reported_location_and_metrics")


class Incident(Record, Base):
    __tablename__ = "incidents"
    location_id: Mapped[str] = mapped_column(ForeignKey("locations.id"), index=True)
    active_key: Mapped[str | None] = mapped_column(String(36), unique=True, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="suspected")
    severity: Mapped[str] = mapped_column(String(20), default="medium")
    owner_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    root_cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    action_taken: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Complaint(Record, Base):
    __tablename__ = "complaints"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    location_id: Mapped[str] = mapped_column(ForeignKey("locations.id"), index=True)
    submission_id: Mapped[str] = mapped_column(String(100))
    reference: Mapped[str] = mapped_column(String(30), unique=True)
    category: Mapped[str] = mapped_column(String(50), index=True)
    description: Mapped[str] = mapped_column(Text)
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    test_id: Mapped[str | None] = mapped_column(ForeignKey("test_attempts.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="submitted", index=True)
    assignee_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    incident_id: Mapped[str | None] = mapped_column(ForeignKey("incidents.id"), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    __table_args__ = (UniqueConstraint("user_id", "submission_id"),)


class TimelineEvent(Record, Base):
    __tablename__ = "timeline_events"
    complaint_id: Mapped[str | None] = mapped_column(
        ForeignKey("complaints.id"), nullable=True, index=True
    )
    incident_id: Mapped[str | None] = mapped_column(
        ForeignKey("incidents.id"), nullable=True, index=True
    )
    actor_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    old_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    new_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    note: Mapped[str] = mapped_column(Text)
    visibility: Mapped[str] = mapped_column(String(20), default="public")
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)


class Maintenance(Record, Base):
    __tablename__ = "maintenance"
    location_id: Mapped[str] = mapped_column(ForeignKey("locations.id"), index=True)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    description: Mapped[str] = mapped_column(Text)
    starts_at: Mapped[datetime] = mapped_column(DateTime)
    ends_at: Mapped[datetime] = mapped_column(DateTime)
    cancelled: Mapped[bool] = mapped_column(Boolean, default=False)


class Notification(Record, Base):
    __tablename__ = "notifications"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    event_key: Mapped[str] = mapped_column(String(180))
    title: Mapped[str] = mapped_column(String(180))
    message: Mapped[str] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    channel: Mapped[str] = mapped_column(String(20), default="in_app")
    delivery_state: Mapped[str] = mapped_column(String(20), default="available")
    __table_args__ = (UniqueConstraint("user_id", "event_key"),)


class Audit(Record, Base):
    __tablename__ = "audit_events"
    actor_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(100))
    entity_id: Mapped[str] = mapped_column(String(36))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
