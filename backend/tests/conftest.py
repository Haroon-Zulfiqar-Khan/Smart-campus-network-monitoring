import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from app.db import Base, make_engine, get_db
from app.models import Campus, User, Building, Location, Endpoint, Threshold
from app.schemas import ThresholdConfig
from app.security import passwords
from app.main import app, requests
from app.measurement import app as measurement


@pytest.fixture()
def system(tmp_path, monkeypatch):
    # Tests must never send fixture complaint data to an external AI provider.
    from app.config import settings
    from pydantic import SecretStr

    monkeypatch.setattr(settings, "gemini_api_key", SecretStr(""))
    engine = make_engine("sqlite:///" + str(tmp_path / "test.db"))
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)

    def db_override():
        with factory() as db:
            try:
                yield db
                db.commit()
            except Exception:
                db.rollback()
                raise

    app.dependency_overrides[get_db] = db_override
    measurement.dependency_overrides[get_db] = db_override
    monkeypatch.setattr("app.models.measurement.SessionLocal", factory)
    monkeypatch.setattr("app.main.SessionLocal", factory)
    requests.clear()
    with factory() as db:
        c = Campus(name="Test Campus")
        other = Campus(name="Other Campus")
        db.add_all([c, other])
        db.flush()
        users = {}
        for name, role in [
            ("admin", "admin"),
            ("it", "support"),
            ("manager", "manager"),
            ("alice", "student"),
            ("bob", "student"),
            ("carol", "student"),
        ]:
            u = User(
                name=name,
                email=name + "@campus.edu",
                password_hash=passwords.hash("Password123!"),
                campus_id=c.id,
                role=role,
            )
            db.add(u)
            db.flush()
            users[name] = u.id
        b = Building(name="Library", campus_id=c.id)
        db.add(b)
        db.flush()
        location = Location(name="Reading Room", building_id=b.id)
        db.add(location)
        e = Endpoint(
            name="Local test endpoint",
            campus_id=c.id,
            base_url="http://testserver/measure",
            operator_healthy=True,
        )
        db.add(e)
        db.add(Threshold(campus_id=c.id, version=1, config=ThresholdConfig().model_dump()))
        db.flush()
        ob = Building(name="Other Building", campus_id=other.id)
        db.add(ob)
        db.flush()
        ol = Location(name="Other Room", building_id=ob.id)
        db.add(ol)
        db.add(Threshold(campus_id=other.id, version=1, config=ThresholdConfig().model_dump()))
        db.flush()
        ids = {
            "campus": c.id,
            "building": b.id,
            "location": location.id,
            "endpoint": e.id,
            "other_campus": other.id,
            "other_location": ol.id,
            **users,
        }
        db.commit()
    with TestClient(app) as api, TestClient(measurement) as measure:
        yield api, measure, ids, factory
    app.dependency_overrides.clear()
    measurement.dependency_overrides.clear()
    engine.dispose()


def login(api, name):
    response = api.post(
        "/auth/login", json={"email": name + "@campus.edu", "password": "Password123!"}
    )
    assert response.status_code == 200, response.text
    data = response.json()
    return {"Authorization": "Bearer " + data["access_token"]}, data


def start(api, ids, headers, key):
    response = api.post(
        "/test-sessions",
        headers=headers,
        json={
            "location_id": ids["location"],
            "endpoint_id": ids["endpoint"],
            "submission_id": key,
            "campus_wifi_confirmed": True,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def run_test(api, measure, ids, headers, key, poor=False):
    session = start(api, ids, headers, key)
    token = {"Authorization": "Bearer " + session["measurement_token"]}
    assert measure.get("/measure/ping", headers=token).status_code == 200
    assert measure.get("/measure/download?bytes=1024", headers=token).status_code == 200
    upload = measure.post("/measure/upload", headers=token, content=b"a" * 1024)
    assert upload.status_code == 200, upload.text
    result = api.post(
        "/test-sessions/" + session["id"] + "/result",
        headers=headers,
        json={
            "status": "completed",
            "download_mbps": 1 if poor else 100,
            "upload_mbps": 1 if poor else 30,
            "latency_ms": 500 if poor else 15,
        },
    )
    assert result.status_code == 200, result.text
    return result.json()
