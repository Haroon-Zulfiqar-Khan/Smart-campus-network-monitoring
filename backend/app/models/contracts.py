from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Role = Literal["student", "staff", "support", "manager", "admin"]
Category = Literal[
    "no_internet",
    "slow_internet",
    "high_ping",
    "frequent_disconnection",
    "weak_signal",
    "service_unavailable",
    "other",
]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, allow_inf_nan=False)

    @field_validator("*", mode="after")
    @classmethod
    def utc_dates(cls, v):
        if isinstance(v, datetime):
            if v.tzinfo is None:
                raise ValueError(
                    "Datetime must include a UTC offset, for example 2026-10-01T05:00:00Z"
                )
            return v.astimezone(timezone.utc).replace(tzinfo=None)
        return v


class Credentials(Input):
    email: str = Field(min_length=5, max_length=254, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    password: str = Field(min_length=10, max_length=128)

    @field_validator("email")
    @classmethod
    def lowercase(cls, v):
        return v.lower()

    @field_validator("password", mode="before")
    @classmethod
    def no_trim(cls, v):
        if isinstance(v, str) and v != v.strip():
            raise ValueError("Password cannot begin or end with whitespace")
        return v


class Register(Credentials):
    name: str = Field(min_length=2, max_length=100)
    campus_id: str


class Refresh(Input):
    refresh_token: str = Field(max_length=300)


class UserCreate(Register):
    role: Role = "student"


class UserUpdate(Input):
    role: Role | None = None
    is_active: bool | None = None


class CampusCreate(Input):
    name: str = Field(min_length=2, max_length=120)
    timezone: str = "Asia/Karachi"

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, v):
        from zoneinfo import ZoneInfo

        try:
            ZoneInfo(v)
        except (KeyError, ValueError):
            raise ValueError("Unknown timezone")
        return v


class BuildingCreate(Input):
    campus_id: str
    name: str = Field(min_length=2, max_length=120)


class LocationCreate(Input):
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    building_id: str
    name: str = Field(min_length=2, max_length=120)
    floor: str = Field(default="Ground", max_length=40)
    description: str = Field(default="", max_length=2000)
    map_x: float | None = Field(default=None, ge=0, le=1)
    map_y: float | None = Field(default=None, ge=0, le=1)


class LocationUpdate(Input):
    floor: str | None = Field(default=None, max_length=40)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    name: str | None = Field(default=None, min_length=2, max_length=120)
    is_active: bool | None = None
    description: str | None = Field(default=None, max_length=2000)


class EndpointCreate(Input):
    campus_id: str
    name: str = Field(min_length=2, max_length=100)
    base_url: str = Field(max_length=500)
    scope: Literal["campus", "internet"] = "campus"

    @field_validator("base_url")
    @classmethod
    def url(cls, v):
        from urllib.parse import urlparse

        p = urlparse(v)
        if (
            p.scheme not in ("http", "https")
            or not p.hostname
            or p.username
            or p.query
            or p.fragment
        ):
            raise ValueError("Expected a plain http/https base URL without credentials or query")
        return v.rstrip("/")


class EndpointUpdate(Input):
    is_active: bool | None = None
    operator_healthy: bool | None = None


class ThresholdConfig(Input):
    good: int = Field(default=75, ge=50, le=99)
    excellent: int = Field(default=90, ge=51, le=100)
    download_target: float = Field(default=100, gt=0, le=10000)
    upload_target: float = Field(default=30, gt=0, le=10000)
    latency_good: float = Field(default=20, ge=0, le=10000)
    latency_bad: float = Field(default=300, gt=0, le=10000)
    weights: dict[str, float] = Field(
        default_factory=lambda: {"download_mbps": 0.35, "upload_mbps": 0.20, "latency_ms": 0.30}
    )
    window_minutes: int = Field(default=60, ge=5, le=1440)
    stale_minutes: int = Field(default=180, ge=10, le=10080)
    minimum_users: int = Field(default=3, ge=2, le=100)
    incident_score: float = Field(default=50, ge=0, le=100)
    recovery_score: float = Field(default=75, ge=0, le=100)
    recovery_users: int = Field(default=2, ge=2, le=100)

    @model_validator(mode="after")
    def bounds(self):
        if self.excellent <= self.good:
            raise ValueError("excellent must exceed good")
        if self.latency_bad <= self.latency_good:
            raise ValueError("latency_bad must exceed latency_good")
        if set(self.weights) != {"download_mbps", "upload_mbps", "latency_ms"} or any(
            v <= 0 or v > 1 for v in self.weights.values()
        ):
            raise ValueError(
                "Supply positive weights <=1 for download_mbps, upload_mbps and latency_ms"
            )
        if self.recovery_score <= self.incident_score:
            raise ValueError("recovery_score must exceed incident_score")
        return self


class StartTest(Input):
    location_id: str
    endpoint_id: str
    submission_id: str = Field(min_length=8, max_length=100)
    campus_wifi_confirmed: bool = False


class TestOutcome(Input):
    status: Literal["completed", "partial", "failed", "cancelled"]
    download_mbps: float | None = Field(default=None, ge=0, le=10000)
    upload_mbps: float | None = Field(default=None, ge=0, le=10000)
    latency_ms: float | None = Field(default=None, ge=0, le=60000)
    jitter_ms: float | None = Field(default=None, ge=0, le=60000)
    reason: str | None = Field(default=None, min_length=3, max_length=500)

    @model_validator(mode="after")
    def consistency(self):
        values = [self.download_mbps, self.upload_mbps, self.latency_ms]
        if self.status == "completed" and any(v is None for v in values):
            raise ValueError("Completed test requires download, upload and application RTT")
        if self.status == "partial" and (
            all(v is None for v in values) or all(v is not None for v in values)
        ):
            raise ValueError("Partial test requires some, but not all, core metrics")
        if self.status in ("failed", "cancelled") and any(
            v is not None for v in values + [self.jitter_ms]
        ):
            raise ValueError("Failed/cancelled attempts cannot contain measurements")
        if self.status != "completed" and not self.reason:
            raise ValueError("Provide a reason for incomplete attempts")
        return self


class ComplaintCreate(Input):
    location_id: str
    category: Category
    description: str = Field(min_length=10, max_length=5000)
    submission_id: str = Field(min_length=8, max_length=100)
    test_id: str | None = None
    occurred_at: datetime | None = None


class Assignment(Input):
    assignee_id: str
    note: str = Field(default="Assigned to support", min_length=3, max_length=2000)


class Note(Input):
    note: str = Field(min_length=3, max_length=2000)
    visibility: Literal["public", "internal"] = "public"


class ComplaintTransition(Input):
    status: Literal[
        "reviewed",
        "in_progress",
        "resolved",
        "reopened",
        "closed",
        "awaiting_user",
        "awaiting_external",
    ]
    note: str = Field(min_length=3, max_length=2000)
    verification_test_ids: list[str] = Field(default_factory=list, max_length=20)


class IncidentTransition(Input):
    status: Literal[
        "confirmed", "investigating", "monitoring_recovery", "resolved", "dismissed", "reopened"
    ]
    note: str = Field(min_length=3, max_length=2000)
    verification_test_ids: list[str] = Field(default_factory=list, max_length=20)
    root_cause: str | None = Field(default=None, max_length=2000)
    action_taken: str | None = Field(default=None, max_length=2000)


class IncidentAssignment(Input):
    owner_id: str
    severity: Literal["low", "medium", "high", "critical"] = "medium"


class MaintenanceCreate(Input):
    location_id: str
    description: str = Field(min_length=10, max_length=2000)
    starts_at: datetime
    ends_at: datetime

    @model_validator(mode="after")
    def ordered(self):
        if self.ends_at <= self.starts_at:
            raise ValueError("Maintenance end must follow start")
        return self
