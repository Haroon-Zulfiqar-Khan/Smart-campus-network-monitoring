from datetime import timedelta
from sqlalchemy import select, func
from conftest import login, start, run_test
from app.models import Incident, TestAttempt, TestResult, Endpoint, now
from app.services import score
from app.schemas import ThresholdConfig
from app.worker import tick


def test_auth_refresh_logout_and_role_boundaries(system):
    api, measure, ids, factory = system
    h, tokens = login(api, "alice")
    assert api.get("/auth/me", headers=h).json()["role"] == "student"
    assert api.get("/admin/users", headers=h).status_code == 403
    assert (
        api.post(
            "/auth/login", json={"email": "alice@campus.edu", "password": "wrongpassword"}
        ).status_code
        == 401
    )
    r = api.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 200
    assert api.get("/auth/me", headers=h).status_code == 401
    assert (
        api.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).status_code
        == 401
    )
    fresh = {"Authorization": "Bearer " + r.json()["access_token"]}
    assert api.post("/auth/logout", headers=fresh).status_code == 200
    assert api.get("/auth/me", headers=fresh).status_code == 401
    assert (
        api.post("/auth/refresh", json={"refresh_token": r.json()["refresh_token"]}).status_code
        == 401
    )


def test_register_cannot_choose_role(system):
    api, _, ids, _ = system
    data = {
        "name": "New Student",
        "email": "new@campus.edu",
        "password": "Password123!",
        "campus_id": ids["campus"],
    }
    assert api.post("/auth/register", json={**data, "role": "admin"}).status_code == 422
    r = api.post("/auth/register", json=data)
    assert r.status_code == 201 and r.json()["user"]["role"] == "student"
    assert "password_hash" not in r.text
    assert api.post("/auth/register", json=data).status_code == 409


def test_measurement_and_result_idempotency(system):
    api, measure, ids, factory = system
    h, _ = login(api, "alice")
    result = run_test(api, measure, ids, h, "measure-0001")
    assert result["result"]["score"] == 100
    assert result["result"]["packet_loss_pct"] is None
    session_id = result["attempt"]["id"]
    body = {"status": "completed", "download_mbps": 100, "upload_mbps": 30, "latency_ms": 15}
    retry = api.post(f"/test-sessions/{session_id}/result", json=body, headers=h)
    assert retry.status_code == 200 and retry.json()["duplicate"]
    assert (
        api.post(
            f"/test-sessions/{session_id}/result", json={**body, "latency_ms": 20}, headers=h
        ).status_code
        == 409
    )
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(TestResult)) == 1
    assert api.get("/tests", headers=h).json()["total"] == 1
    h2, _ = login(api, "bob")
    assert api.get("/tests/" + session_id, headers=h2).status_code == 403
    assert (
        api.post("/test-sessions/" + session_id + "/result", headers=h2, json=body).status_code
        == 403
    )


def test_measurement_token_isolation_size_and_confirmed_upload(system, monkeypatch):
    api, measure, ids, _ = system
    h, t = login(api, "alice")
    s = start(api, ids, h, "limits-0001")
    mh = {"Authorization": "Bearer " + s["measurement_token"]}
    assert measure.get("/measure/ping", headers=h).status_code == 401
    assert api.get("/auth/me", headers=mh).status_code == 401
    assert measure.get("/measure/download?bytes=999999999", headers=mh).status_code == 422
    assert measure.post("/measure/upload", headers=mh, content=b"").status_code == 422
    r = api.post(
        "/test-sessions/" + s["id"] + "/result",
        headers=h,
        json={"status": "completed", "download_mbps": 90, "upload_mbps": 20, "latency_ms": 30},
    )
    assert r.status_code == 422
    monkeypatch.setattr("app.measurement.settings.max_session_bytes", 1024)
    assert measure.get("/measure/download?bytes=1024", headers=mh).status_code == 200
    assert measure.get("/measure/download?bytes=1024", headers=mh).status_code == 429


def test_partial_failed_cancelled_and_expiry(system):
    api, measure, ids, factory = system
    h, _ = login(api, "alice")
    s = start(api, ids, h, "partial-0001")
    r = api.post(
        "/test-sessions/" + s["id"] + "/result",
        headers=h,
        json={"status": "partial", "download_mbps": 0, "reason": "Upload endpoint unreachable"},
    )
    assert r.status_code == 200
    assert r.json()["result"]["score"] is None and r.json()["result"]["upload_mbps"] is None
    assert r.json()["result"]["download_mbps"] == 0
    assert api.get("/locations/" + ids["location"], headers=h).json()["health"] == "unknown"
    s2 = start(api, ids, h, "failed-0001")
    assert (
        api.post(
            "/test-sessions/" + s2["id"] + "/result",
            headers=h,
            json={"status": "failed", "download_mbps": 0, "reason": "unreachable"},
        ).status_code
        == 422
    )
    assert (
        api.post(
            "/test-sessions/" + s2["id"] + "/result",
            headers=h,
            json={"status": "failed", "reason": "Endpoint unreachable"},
        ).status_code
        == 200
    )
    s3 = start(api, ids, h, "expire-0001")
    with factory() as db:
        db.get(TestAttempt, s3["id"]).expires_at = now() - timedelta(minutes=1)
        tick(db)
        db.commit()
    assert api.get("/tests/" + s3["id"], headers=h).json()["attempt"]["status"] == "failed"
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(Incident)) == 0


def test_scope_privacy_filters_and_notifications(system):
    api, measure, ids, factory = system
    alice, _ = login(api, "alice")
    bob, _ = login(api, "bob")
    it, _ = login(api, "it")
    assert api.get("/locations/" + ids["other_location"], headers=alice).status_code == 403
    data = {
        "location_id": ids["location"],
        "category": "slow_internet",
        "description": "Wi-Fi becomes very slow in this room",
        "submission_id": "complaint-private",
    }
    r = api.post("/complaints", headers=alice, json=data)
    assert r.status_code == 201, r.text
    c = r.json()
    id = c["id"]
    assert api.post("/complaints", headers=alice, json=data).json()["duplicate"]
    assert (
        api.post(
            "/complaints", headers=alice, json={**data, "description": "Different problem here"}
        ).status_code
        == 409
    )
    assert api.get("/complaints/" + id, headers=bob).status_code == 403
    assert api.get("/complaints", headers=bob).json()["total"] == 0
    assert (
        api.post(
            f"/complaints/{id}/notes",
            headers=it,
            json={"note": "Confidential switch information", "visibility": "internal"},
        ).status_code
        == 201
    )
    assert "Confidential" not in api.get("/complaints/" + id, headers=alice).text
    assert "Confidential" in api.get("/complaints/" + id, headers=it).text
    assert (
        api.patch(
            "/complaints/" + id + "/assignment", headers=alice, json={"assignee_id": ids["it"]}
        ).status_code
        == 403
    )
    assert api.get("/complaints?category=no_internet", headers=it).json()["total"] == 0
    assert api.get("/notifications", headers=alice).json()["total"] >= 1
    notif = api.get("/notifications", headers=alice).json()["items"][0]["id"]
    assert api.patch("/notifications/" + notif + "/read", headers=bob).status_code == 403
    assert api.patch("/notifications/" + notif + "/read", headers=alice).json()["is_read"] is True


def test_full_complaint_resolution_requires_evidence(system):
    api, measure, ids, factory = system
    alice, _ = login(api, "alice")
    it, _ = login(api, "it")
    poor = run_test(api, measure, ids, alice, "bad-test-0001", poor=True)
    c = api.post(
        "/complaints",
        headers=alice,
        json={
            "location_id": ids["location"],
            "category": "slow_internet",
            "description": "Very slow Wi-Fi; please check this room",
            "submission_id": "full-complaint-0001",
            "test_id": poor["attempt"]["id"],
        },
    ).json()
    path = "/complaints/" + c["id"]

    def status(value, **kw):
        return api.post(
            path + "/transitions",
            headers=it,
            json={"status": value, "note": "Investigation update", **kw},
        )

    assert (
        api.post(
            path + "/transitions",
            headers=alice,
            json={"status": "resolved", "note": "Student must not resolve complaints"},
        ).status_code
        == 403
    )
    assert status("reviewed").status_code == 200
    assert (
        api.patch(path + "/assignment", headers=it, json={"assignee_id": ids["it"]}).status_code
        == 200
    )
    assert status("in_progress").status_code == 200
    assert status("resolved").status_code == 200
    healthy = run_test(api, measure, ids, alice, "recovery-0001")
    resolved = status("resolved", verification_test_ids=[healthy["attempt"]["id"]])
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["resolved_at"]
    assert (
        api.post(
            path + "/transitions",
            headers=alice,
            json={"status": "reopened", "note": "The problem has returned again"},
        ).status_code
        == 200
    )
    assert status("in_progress").status_code == 200
    assert status("resolved").status_code == 200


def test_incident_independence_dedup_health_and_verified_recovery(system):
    api, measure, ids, factory = system
    hs = {name: login(api, name)[0] for name in ("alice", "bob", "carol", "it")}
    for i in range(3):
        run_test(api, measure, ids, hs["alice"], "same-user-" + str(i), poor=True)
    assert api.get("/incidents", headers=hs["it"]).json()["total"] == 0
    for name in ("bob", "carol"):
        run_test(api, measure, ids, hs[name], "poor-" + name + "-001", poor=True)
    listing = api.get("/incidents", headers=hs["it"]).json()
    assert listing["total"] == 1
    incident = listing["items"][0]
    id = incident["id"]
    path = "/incidents/" + id
    assert (
        api.get("/locations/" + ids["location"], headers=hs["alice"]).json()["operational_status"]
        == "suspected_outage"
    )
    assert "evidence" not in api.get("/incidents", headers=hs["alice"]).json()["items"][0]
    run_test(api, measure, ids, hs["bob"], "poor-bob-002", poor=True)
    assert api.get("/incidents", headers=hs["it"]).json()["total"] == 1
    assert (
        api.patch(
            path + "/assignment", headers=hs["it"], json={"owner_id": ids["it"], "severity": "high"}
        ).status_code
        == 200
    )
    for value in ("confirmed", "investigating", "monitoring_recovery"):
        r = api.post(
            path + "/transitions",
            headers=hs["it"],
            json={"status": value, "note": "IT operational update"},
        )
        assert r.status_code == 200, r.text
    tests = [
        run_test(api, measure, ids, hs[name], "healthy-" + name + "-001")["attempt"]["id"]
        for name in ("alice", "bob")
    ]
    data = {
        "status": "resolved",
        "note": "Wi-Fi performance restored",
        "root_cause": "Uplink configuration",
        "action_taken": "Corrected uplink",
        "verification_test_ids": tests[:1],
    }
    assert api.post(path + "/transitions", headers=hs["it"], json=data).status_code == 422
    r = api.post(
        path + "/transitions", headers=hs["it"], json={**data, "verification_test_ids": tests}
    )
    assert r.status_code == 200, r.text
    assert r.json()["active_key"] is None
    assert (
        api.post(
            path + "/transitions",
            headers=hs["it"],
            json={"status": "reopened", "note": "The issue returned after repair"},
        ).status_code
        == 200
    )


def test_endpoint_unhealthy_and_maintenance_suppress_incidents(system):
    api, measure, ids, factory = system
    it, _ = login(api, "it")
    with factory() as db:
        db.get(Endpoint, ids["endpoint"]).operator_healthy = False
        db.commit()
    for name in ("alice", "bob", "carol"):
        run_test(api, measure, ids, login(api, name)[0], "unhealthy-" + name, poor=True)
    assert api.get("/incidents", headers=it).json()["total"] == 0
    maintenance = {
        "location_id": ids["location"],
        "description": "Scheduled access point maintenance",
        "starts_at": (now() - timedelta(minutes=1)).isoformat() + "Z",
        "ends_at": (now() + timedelta(minutes=10)).isoformat() + "Z",
    }
    r = api.post("/maintenance", headers=it, json=maintenance)
    assert r.status_code == 201, r.text
    with factory() as db:
        db.get(Endpoint, ids["endpoint"]).operator_healthy = True
        tick(db)
        db.commit()
    assert api.get("/incidents", headers=it).json()["total"] == 0
    assert (
        api.get("/locations/" + ids["location"], headers=it).json()["operational_status"]
        == "maintenance"
    )
    assert api.post("/maintenance/" + r.json()["id"] + "/cancel", headers=it).status_code == 200
    with factory() as db:
        tick(db)
        db.commit()
    assert api.get("/incidents", headers=it).json()["total"] == 1


def test_dashboard_analytics_threshold_version_and_stale(system):
    api, measure, ids, factory = system
    alice, _ = login(api, "alice")
    it, _ = login(api, "it")
    admin, _ = login(api, "admin")
    first = run_test(api, measure, ids, alice, "analytics-0001")
    config = ThresholdConfig(download_target=200).model_dump()
    r = api.post("/admin/thresholds", headers=admin, json=config)
    assert r.status_code == 201, r.text
    second = run_test(api, measure, ids, alice, "analytics-0002")
    assert first["result"]["threshold_version"] == 1 and second["result"]["threshold_version"] == 2
    assert second["result"]["score"] < first["result"]["score"]
    assert (
        api.get("/tests/" + first["attempt"]["id"], headers=alice).json()["result"]["score"] == 100
    )
    dashboard = api.get("/dashboard", headers=it).json()
    assert dashboard["counts"]["tests_today"] == 2
    assert dashboard["metrics"]["average_download_mbps"] == 100
    assert (
        api.get("/dashboard?building_id=unknown", headers=it).json()["counts"]["tests_today"] == 0
    )
    analytics = api.get("/analytics", headers=it).json()
    assert analytics["buildings"][0]["tests"] == 2 and analytics["daily"][0]["samples"] == 2
    assert api.get("/analytics", headers=alice).status_code == 403
    assert api.get("/reports/tests.csv", headers=it).status_code == 200
    assert api.get("/dashboard?since=2026-01-01T00:00:00", headers=it).status_code == 422
    with factory() as db:
        for a in db.scalars(select(TestAttempt)):
            a.finished_at = now() - timedelta(days=1)
        db.commit()
    assert (
        api.get("/locations/" + ids["location"], headers=it).json()["operational_status"] == "stale"
    )


def test_score_missing_data_and_null_are_different_from_zero():
    config = ThresholdConfig().model_dump()
    value, health, why = score({"download_mbps": 0, "upload_mbps": None, "latency_ms": 300}, config)
    assert value == 0 and health == "critical"
    assert "upload_mbps" in why["missing"]
    value, health, why = score(
        {"download_mbps": 100, "upload_mbps": 30, "latency_ms": None}, config
    )
    assert value == 100 and health == "excellent"
    assert why["measurement_coverage"] < 1
