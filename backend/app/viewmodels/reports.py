import csv
import io
from collections import defaultdict, Counter
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from statistics import mean
from ..errors import DomainError as HTTPException
from sqlalchemy import select
from ..models import Campus, Building, now
from ..models.reporting import collect, average_metrics


class ReportsViewModel:
    """Orchestrates use cases and prepares state consumed by API Views."""

    @staticmethod
    def dashboard(
        location_id: str | None = None,
        building_id: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        network_status: str | None = None,
        category: str | None = None,
        complaint_status: str | None = None,
        user=None,
        db=None,
    ):
        locations, attempts, results, complaints, incidents = collect(
            db,
            user,
            location_id,
            building_id,
            since,
            until,
            network_status,
            category,
            complaint_status,
        )
        tz = ZoneInfo(db.get(Campus, user.campus_id).timezone)
        today = now().replace(tzinfo=timezone.utc).astimezone(tz).date()
        today_attempts = [
            a
            for a in attempts
            if a.created_at.replace(tzinfo=timezone.utc).astimezone(tz).date() == today
        ]
        today_results = [results[a.id] for a in today_attempts if a.id in results]
        counts = {
            "tests_today": len(today_attempts),
            "tests_in_range": len(attempts),
            "poor_locations": sum(
                (location["health"] in ("poor", "critical") for location in locations)
            ),
            "open_complaints": sum((c.status not in ("resolved", "closed") for c in complaints)),
            "resolved_complaints": sum((c.status in ("resolved", "closed") for c in complaints)),
            "active_incidents": len(incidents),
            "confirmed_outages": sum((i.status != "suspected" for i in incidents)),
        }
        per_location = []
        for location in locations:
            own = [a for a in attempts if a.location_id == location["id"]]
            per_location.append(
                {
                    **location,
                    "tests_in_range": len(own),
                    "complaints_in_range": sum(
                        (c.location_id == location["id"] for c in complaints)
                    ),
                }
            )
        personal = {
            "tests": sum((a.user_id == user.id for a in attempts)),
            "open_complaints": sum(
                (
                    c.user_id == user.id and c.status not in ("resolved", "closed")
                    for c in complaints
                )
            ),
        }
        return {
            "counts": counts,
            "metrics": average_metrics(results.values()),
            "today_metrics": average_metrics(today_results),
            "locations": per_location,
            "personal": personal,
            "timezone": str(tz),
            "as_of": now().isoformat() + "Z",
            "notes": [
                "Location health uses recent independent-user samples; counts and metric averages use the requested date range.",
                "Unknown and stale observations are not evidence of healthy service.",
            ],
        }

    @staticmethod
    def analytics(
        location_id: str | None = None,
        building_id: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        network_status: str | None = None,
        category: str | None = None,
        complaint_status: str | None = None,
        user=None,
        db=None,
    ):
        locations, attempts, results, complaints, incidents = collect(
            db,
            user,
            location_id,
            building_id,
            since,
            until,
            network_status,
            category,
            complaint_status,
        )
        tz = ZoneInfo(db.get(Campus, user.campus_id).timezone)
        hourly = defaultdict(list)
        daily = defaultdict(list)
        for a in attempts:
            if a.id not in results:
                continue
            local = a.created_at.replace(tzinfo=timezone.utc).astimezone(tz)
            hourly[local.strftime("%Y-%m-%dT%H:00%z")].append(results[a.id])
            daily[local.strftime("%Y-%m-%d")].append(results[a.id])
        buildings = list(db.scalars(select(Building).where(Building.campus_id == user.campus_id)))
        location_building = {location["id"]: location["building_id"] for location in locations}
        building_rows = []
        for b in buildings:
            ar = [a for a in attempts if location_building.get(a.location_id) == b.id]
            cr = [c for c in complaints if location_building.get(c.location_id) == b.id]
            building_rows.append(
                {
                    "building_id": b.id,
                    "name": b.name,
                    "tests": len(ar),
                    "complaints": len(cr),
                    **average_metrics([results[a.id] for a in ar if a.id in results]),
                }
            )
        times = [
            (c.resolved_at - c.created_at).total_seconds() / 60 for c in complaints if c.resolved_at
        ]
        workload = Counter(
            (
                c.assignee_id
                for c in complaints
                if c.assignee_id and c.status not in ("resolved", "closed")
            )
        )
        rankings = []
        for location in locations:
            n = sum((c.location_id == location["id"] for c in complaints))
            if n or location["health"] in ("poor", "critical"):
                rankings.append(
                    {
                        "location_id": location["id"],
                        "name": location["name"],
                        "complaints": n,
                        "score": location["score"],
                        "priority": round(
                            (100 - location["score"] if location["score"] is not None else 0)
                            + n * 5,
                            2,
                        ),
                        "recommendation": "Review endpoint health, repeat measurements and investigate recurring symptoms with IT.",
                    }
                )
        rankings.sort(key=lambda r: r["priority"], reverse=True)
        trend = []
        for location in locations:
            lr = [
                (a, results[a.id])
                for a in attempts
                if a.location_id == location["id"]
                and a.id in results
                and (results[a.id].score is not None)
            ]
            lr.sort(key=lambda pair: pair[0].created_at)
            if len(lr) >= 6:
                split = len(lr) // 2
                before = mean((r.score for _, r in lr[:split]))
                after = mean((r.score for _, r in lr[split:]))
                trend.append(
                    {
                        "location_id": location["id"],
                        "baseline_score": round(before, 2),
                        "recent_score": round(after, 2),
                        "change": round(after - before, 2),
                        "method": "Earlier half versus later half of selected observed tests; exploratory, not a forecast",
                    }
                )
        return {
            "hourly": [
                {"period": k, "samples": len(v), **average_metrics(v)}
                for k, v in sorted(hourly.items())
            ],
            "daily": [
                {"period": k, "samples": len(v), **average_metrics(v)}
                for k, v in sorted(daily.items())
            ],
            "buildings": building_rows,
            "complaints_by_category": dict(Counter((c.category for c in complaints))),
            "complaints_by_status": dict(Counter((c.status for c in complaints))),
            "average_resolution_minutes": round(mean(times), 2) if times else None,
            "staff_workload": [{"user_id": id, "open_complaints": n} for id, n in workload.items()],
            "problem_locations": rankings,
            "trends": trend,
            "timezone": str(tz),
            "summary": f"{len(attempts)} test attempts, {len(complaints)} complaints and {len(incidents)} active incidents match these filters.",
            "limitations": "Rule-based insights on sampled observations. No traffic telemetry, machine-learning prediction or verified network utilization.",
        }

    @staticmethod
    def export(
        location_id: str | None = None,
        building_id: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        user=None,
        db=None,
    ):
        _, attempts, results, _, _ = collect(db, user, location_id, building_id, since, until)
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(
            [
                "test_id",
                "location_id",
                "timestamp_utc",
                "outcome",
                "download_mbps",
                "upload_mbps",
                "application_rtt_ms",
                "score",
                "health",
            ]
        )
        for a in attempts:
            r = results.get(a.id)
            writer.writerow(
                [
                    a.id,
                    a.location_id,
                    a.created_at.isoformat() + "Z",
                    a.status,
                    *(
                        [r.download_mbps, r.upload_mbps, r.latency_ms, r.score, r.health]
                        if r
                        else [None] * 5
                    ),
                ]
            )
        return {"content": out.getvalue(), "media_type": "text/csv"}

    @staticmethod
    def classify(data: dict, user=None):
        text = data.get("description", "")
        if not isinstance(text, str) or len(text) > 5000:
            raise HTTPException(422, "Provide description text of at most 5000 characters")
        rules = {
            "no_internet": ["no internet", "offline", "cannot connect"],
            "slow_internet": ["slow", "buffer", "download"],
            "high_ping": ["ping", "latency", "lag"],
            "frequent_disconnection": ["disconnect", "drops", "intermittent"],
            "weak_signal": ["signal", "range"],
            "service_unavailable": ["website", "service", "dns"],
        }
        scores = {
            cat: sum((term in text.lower() for term in terms)) for cat, terms in rules.items()
        }
        best = max(scores, key=scores.get)
        return {
            "suggested_category": best if scores[best] else "other",
            "method": "keyword rules",
            "user_confirmation_required": True,
        }
