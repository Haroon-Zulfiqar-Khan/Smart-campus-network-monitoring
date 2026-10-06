from conftest import login, run_test
from app.models import gemini
from app.models.gemini import Insight


def create(api, headers, location, key="ai-complaint-0001"):
    return api.post(
        "/complaints",
        headers=headers,
        json={
            "location_id": location,
            "category": "other",
            "description": "The Wi-Fi disconnects every few minutes during class.",
            "submission_id": key,
        },
    )


def test_automatic_classification_and_retry_preserve_original_input(system, monkeypatch):
    api, measure, ids, factory = system
    calls = []

    def classify(description):
        calls.append(description)
        return {
            "category": "frequent_disconnection",
            "confidence": 0.95,
            "reason": "Repeated connection drops.",
            "method": "gemini",
            "model": "test-model",
            "warning": None,
        }

    monkeypatch.setattr(gemini, "classify", classify)
    student, _ = login(api, "alice")
    admin, _ = login(api, "admin")
    first = create(api, student, ids["location"])
    assert first.status_code == 201, first.text
    assert first.json()["category"] == "frequent_disconnection"
    retry = create(api, student, ids["location"])
    assert retry.status_code == 201, retry.text
    assert retry.json()["duplicate"] and len(calls) == 1
    rows = api.get("/admin/ai", headers=admin).json()["complaints"]
    assert rows[0]["analysis"]["method"] == "gemini" and rows[0]["analysis"]["applied"]
    assert rows[0]["analysis"]["original_category"] == "other"
    assert api.get("/admin/ai", headers=student).status_code == 403
    assert api.post("/admin/ai/network-summary", headers=student).status_code == 403


def test_keyword_fallback_is_labelled_and_admin_can_apply(system):
    api, measure, ids, factory = system
    student, _ = login(api, "alice")
    admin, _ = login(api, "admin")
    result = create(api, student, ids["location"])
    assert result.json()["category"] == "other"
    row = api.get("/admin/ai", headers=admin).json()["complaints"][0]
    assert row["analysis"]["method"] == "keyword_rules" and not row["analysis"]["applied"]
    assert row["analysis"]["warning"] and row["analysis"]["category"] == "frequent_disconnection"
    applied = api.post("/admin/ai/complaints/" + result.json()["id"] + "/apply", headers=admin)
    assert applied.status_code == 200 and applied.json()["category"] == "frequent_disconnection"
    assert (
        api.post(
            "/admin/ai/complaints/" + result.json()["id"] + "/apply", headers=student
        ).status_code
        == 403
    )


def test_summary_uses_scoped_aggregates_and_persists(system, monkeypatch):
    api, measure, ids, factory = system
    student, _ = login(api, "alice")
    admin, _ = login(api, "admin")
    run_test(api, measure, ids, student, "ai-summary-test-0001")
    create(api, student, ids["location"])
    captured = []

    def generate(instruction, facts, output_type):
        captured.append(facts)
        return Insight(
            summary="One recorded observation and one complaint need review.",
            observations=["A recurring disconnection was reported."],
            recommendations=["Inspect the affected access point."],
            limitations=["The sample is small."],
        )

    monkeypatch.setattr(gemini, "generate", generate)
    result = api.post("/admin/ai/network-summary?hours=72", headers=admin)
    assert result.status_code == 200, result.text
    data = result.json()
    assert data["method"] == "gemini" and data["facts"]["test_count"] == 1
    assert data["facts"]["complaint_count"] == 1
    assert "alice@campus.edu" not in str(captured) and ids["alice"] not in str(captured)
    assert api.get("/admin/ai", headers=admin).json()["last_summary"]["summary"] == data["summary"]
    assert api.post("/admin/ai/network-summary?hours=72", headers=admin).status_code == 429
    assert api.post("/admin/ai/network-summary?hours=2", headers=admin).status_code == 422


def test_ai_classification_cannot_cross_campus(system, monkeypatch):
    api, measure, ids, factory = system
    registered = api.post(
        "/auth/register",
        json={
            "name": "Outside student",
            "email": "outsider@campus.edu",
            "password": "Password123!",
            "campus_id": ids["other_campus"],
        },
    )
    assert registered.status_code == 201, registered.text
    other, _ = login(api, "outsider")
    admin, _ = login(api, "admin")
    complaint = create(api, other, ids["other_location"]).json()

    def forbidden(*args):
        raise AssertionError("Unauthorized data must not be sent to Gemini")

    monkeypatch.setattr(gemini, "classify", forbidden)
    assert (
        api.post("/admin/ai/complaints/" + complaint["id"] + "/classify", headers=admin).status_code
        == 403
    )
    assert api.get("/admin/ai", headers=admin).json()["complaints"] == []


def test_provider_key_is_server_only_and_input_contacts_are_removed(monkeypatch):
    from app.config import settings
    from pydantic import SecretStr
    import json
    import httpx

    monkeypatch.setattr(settings, "gemini_api_key", SecretStr("test-secret-not-a-real-key"))
    monkeypatch.setattr(gemini, "_unavailable_until", 0)
    requests = []

    def post(url, headers, json, timeout):
        requests.append({"url": url, "headers": headers, "payload": json})
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": '{"category":"slow_internet","confidence":0.9,"reason":"Reported slow download."}'
                                }
                            ]
                        }
                    }
                ]
            },
        )

    monkeypatch.setattr(gemini.httpx, "post", post)
    result = gemini.classify("Slow download. Contact alice@example.edu or +923001234567.")
    assert result["method"] == "gemini"
    assert requests[0]["headers"]["x-goog-api-key"] == "test-secret-not-a-real-key"
    payload = json.dumps(requests[0]["payload"])
    assert "alice@example.edu" not in payload and "+923001234567" not in payload
    assert "test-secret-not-a-real-key" not in payload
