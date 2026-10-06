import pytest
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, func
from app.db import Base, make_engine
from app.models import Campus, User, Threshold
from app.render_start import prepare_environment, initialize_campus


def test_render_environment_adapts_driver_and_public_measurement_url():
    env = {
        "DATABASE_URL": "postgresql://test:dummy@host/campus",
        "RENDER_EXTERNAL_URL": "https://example.onrender.com/",
    }
    prepare_environment(env)
    assert env["DATABASE_URL"] == "postgresql+psycopg://test:dummy@host/campus"
    assert env["MEASUREMENT_BASE_URL"] == "https://example.onrender.com/probe/measure"
    with pytest.raises(RuntimeError, match="HTTPS"):
        prepare_environment({"RENDER_EXTERNAL_URL": "http://localhost"})


def test_initialization_is_idempotent_and_does_not_reset_password(tmp_path):
    engine = make_engine("sqlite:///" + str(tmp_path / "bootstrap.db"))
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine)
    with factory() as db:
        env = {"INITIAL_ADMIN_EMAIL": "admin@example.edu", "INITIAL_ADMIN_PASSWORD": "TestOnly123!"}
        assert initialize_campus(db, env)
        original = db.scalar(select(User)).password_hash
        assert not initialize_campus(db, {**env, "INITIAL_ADMIN_PASSWORD": "Changed123!"})
        assert db.scalar(select(User)).password_hash == original
        assert db.scalar(select(func.count()).select_from(Campus)) == 1
        assert db.scalar(select(func.count()).select_from(Threshold)) == 1
    engine.dispose()


def test_invalid_bootstrap_does_not_leak_password_or_create_campus(tmp_path):
    engine = make_engine("sqlite:///" + str(tmp_path / "invalid.db"))
    Base.metadata.create_all(engine)
    with sessionmaker(engine)() as db:
        with pytest.raises(RuntimeError) as error:
            initialize_campus(
                db, {"INITIAL_ADMIN_EMAIL": "invalid", "INITIAL_ADMIN_PASSWORD": "private"}
            )
        assert "private" not in str(error.value)
        assert db.scalar(select(func.count()).select_from(Campus)) == 0
    engine.dispose()


def test_combined_host_serves_api_measurements_and_cors(system, monkeypatch):
    from fastapi.testclient import TestClient
    from app import main, render_app

    api, measurement, ids, factory = system
    monkeypatch.setattr(main, "SessionLocal", factory)
    monkeypatch.setattr(render_app, "run_tick", lambda: None)
    with TestClient(render_app.app) as client:
        assert client.get("/health/live").status_code == 200
        assert client.get("/probe/health/live").status_code == 200
        response = client.get("/auth/campuses")
        assert response.status_code == 200
        response = client.options("/auth/login", headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        })
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
