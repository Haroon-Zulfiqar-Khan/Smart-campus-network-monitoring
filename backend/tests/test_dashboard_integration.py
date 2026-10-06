from conftest import login, run_test


def test_internet_test_and_complaint_attachment(system):
    api, measure, ids, factory = system
    student, _ = login(api, "alice")
    start = api.post(
        "/workspace/internet-test-sessions",
        headers=student,
        json={"location_id": ids["location"], "submission_id": "internet-test-001"},
    )
    assert start.status_code == 201, start.text
    session = start.json()
    assert session["base_url"] == "https://speed.cloudflare.com"
    assert session["transport"] == "cloudflare"
    assert (
        api.post(
            "/workspace/internet-test-sessions",
            headers=student,
            json={"location_id": ids["other_location"], "submission_id": "outside-internet"},
        ).status_code
        == 403
    )
    saved = api.post(
        "/test-sessions/" + session["id"] + "/result",
        headers=student,
        json={"status": "completed", "download_mbps": 42.5, "upload_mbps": 12.4, "latency_ms": 30},
    )
    assert saved.status_code == 200, saved.text
    complaint = api.post(
        "/complaints",
        headers=student,
        json={
            "location_id": ids["location"],
            "category": "slow_internet",
            "description": "The internet connection is slower than usual.",
            "submission_id": "internet-complaint-001",
            "test_id": session["id"],
        },
    )
    assert complaint.status_code == 201, complaint.text
    assert complaint.json()["test_id"] == session["id"]
    snapshot = api.get("/workspace", headers=student).json()
    attached = next(c for c in snapshot["complaints"] if c["id"] == complaint.json()["id"])[
        "attachedTest"
    ]
    assert attached["id"] == session["id"] and attached["download"] == 42.5
    it, _ = login(api, "it")
    # Directly resolve from Submitted, without assignment, note or verification tests.
    resolved = api.patch(
        "/workspace/complaints/" + complaint.json()["id"],
        headers=it,
        json={"status": "Resolved", "note": ""},
    )
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["status"] == "resolved"
    failed_session = api.post(
        "/workspace/internet-test-sessions",
        headers=student,
        json={"location_id": ids["location"], "submission_id": "internet-test-failed"},
    ).json()
    assert (
        api.post(
            "/test-sessions/" + failed_session["id"] + "/result",
            headers=student,
            json={"status": "failed", "reason": "Internet endpoint unreachable."},
        ).status_code
        == 200
    )
    failed_complaint = api.post(
        "/complaints",
        headers=student,
        json={
            "location_id": ids["location"],
            "category": "no_internet",
            "description": "No external internet connection is available.",
            "submission_id": "offline-complaint-001",
            "test_id": failed_session["id"],
        },
    ).json()
    failed_attachment = next(
        c
        for c in api.get("/workspace", headers=student).json()["complaints"]
        if c["id"] == failed_complaint["id"]
    )["attachedTest"]
    assert failed_attachment["outcome"] == "failed" and failed_attachment["download"] is None


def test_workspace_map_permissions_and_notes(system):
    api, measure, ids, factory = system
    student, _ = login(api, "alice")
    it, _ = login(api, "it")
    admin, _ = login(api, "admin")
    manager, _ = login(api, "manager")
    assert api.get("/workspace").status_code == 401
    r = api.post(
        "/workspace/locations",
        headers=student,
        json={"name": "Courtyard", "latitude": 25.406, "longitude": 68.26},
    )
    assert r.status_code == 201, r.text
    loc = r.json()["id"]
    assert r.json()["user_reported"]
    assert (
        api.patch(
            "/workspace/locations/" + loc,
            headers=student,
            json={"name": "Changed", "latitude": 25, "longitude": 68},
        ).status_code
        == 403
    )
    assert (
        api.patch(
            "/workspace/locations/" + loc,
            headers=admin,
            json={
                "name": "Library Courtyard",
                "building": "Library",
                "floor": "Ground",
                "latitude": 25.407,
                "longitude": 68.261,
            },
        ).status_code
        == 200
    )
    assert (
        api.post(
            "/workspace/locations",
            headers=student,
            json={"name": "Bad", "latitude": 91, "longitude": 68},
        ).status_code
        == 422
    )
    assert (
        api.post(
            "/workspace/locations", headers=student, json={"name": "Partial", "latitude": 25}
        ).status_code
        == 422
    )
    assert (
        api.post(
            "/workspace/maintenance-notes",
            headers=it,
            json={"location_id": loc, "text": "Access point inspected; connection verified."},
        ).status_code
        == 201
    )
    assert any(
        n["locationId"] == loc
        for n in api.get("/workspace", headers=manager).json()["maintenanceNotes"]
    )
    assert (
        api.post(
            "/workspace/maintenance-notes",
            headers=it,
            json={"location_id": ids["other_location"], "text": "Outside campus maintenance note."},
        ).status_code
        == 403
    )
    assert (
        api.patch(
            "/workspace/permissions/support", headers=admin, json={"permissions": []}
        ).status_code
        == 200
    )
    assert (
        api.post(
            "/workspace/maintenance-notes",
            headers=it,
            json={"location_id": loc, "text": "Not allowed after permission removal."},
        ).status_code
        == 403
    )
    assert api.get("/tests?mine=false", headers=it).status_code == 403
    assert api.get("/tests?mine=0", headers=it).status_code == 403
    assert api.get("/complaints", headers=it).status_code == 403
    assert api.get("/workspace", headers=it).json()["maintenanceNotes"] == []
    assert (
        api.patch(
            "/workspace/permissions/admin", headers=admin, json={"permissions": []}
        ).status_code
        == 422
    )


def test_atomic_complaint_update_and_manual_resolution(system):
    api, measure, ids, factory = system
    student, _ = login(api, "alice")
    it, _ = login(api, "it")
    r = api.post(
        "/complaints",
        headers=student,
        json={
            "location_id": ids["location"],
            "category": "slow_internet",
            "description": "The network is slow in the reading room.",
            "submission_id": "integration-complaint",
        },
    )
    cid = r.json()["id"]
    assert (
        api.patch(
            "/workspace/complaints/" + cid,
            headers=it,
            json={
                "status": "Resolved",
                "assignee_id": "missing-assignee",
                "note": "Manual resolution.",
            },
        ).status_code
        == 404
    )
    assert api.get("/complaints/" + cid, headers=it).json()["status"] == "submitted"
    assert (
        api.patch(
            "/workspace/complaints/" + cid,
            headers=it,
            json={
                "status": "Assigned",
                "assignee_id": ids["it"],
                "note": "Assigned for investigation.",
            },
        ).status_code
        == 200
    )
    assert any(
        "Assigned" in a["message"] or "assigned" in a["message"]
        for a in api.get("/workspace", headers=student).json()["alerts"]
    )
    run_test(api, measure, ids, student, "integration-test-one")
    bob, _ = login(api, "bob")
    run_test(api, measure, ids, bob, "integration-test-two")
    result = api.patch(
        "/workspace/complaints/" + cid,
        headers=it,
        json={
            "status": "Resolved",
            "assignee_id": ids["it"],
            "note": "",
        },
    )
    assert result.status_code == 200, result.text
    assert result.json()["status"] == "resolved"
    snap = api.get("/workspace", headers=student).json()
    assert len(snap["tests"]) == 1 and len(snap["networkHistory"]) == 2
    assert all("owner" not in t for t in snap["networkHistory"])
