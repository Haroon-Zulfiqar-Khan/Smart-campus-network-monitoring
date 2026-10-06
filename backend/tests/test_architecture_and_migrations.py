import ast
import os
from pathlib import Path
import subprocess
import sys
from sqlalchemy import create_engine, inspect
from app.models.contracts import Credentials
from app.viewmodels.auth import AuthViewModel
from app.errors import DomainError

ROOT = Path(__file__).resolve().parents[1]


def test_views_delegate_and_viewmodels_have_no_http_framework_imports():
    for path in (ROOT / "app/viewmodels").glob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert not (node.module or "").startswith(("fastapi", "starlette"))
    for path in (ROOT / "app/views").glob("*.py"):
        tree = ast.parse(path.read_text())
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.decorator_list:
                assert any(
                    isinstance(call, ast.Call)
                    and isinstance(call.func, ast.Attribute)
                    and isinstance(call.func.value, ast.Name)
                    and call.func.value.id == "viewmodel"
                    for call in ast.walk(node)
                ), path.name
                assert not any(
                    isinstance(call, ast.Call)
                    and isinstance(call.func, ast.Attribute)
                    and isinstance(call.func.value, ast.Name)
                    and call.func.value.id == "db"
                    for call in ast.walk(node)
                ), path.name


def test_frozen_initial_migration_and_no_schema_drift(tmp_path):
    env = {**os.environ, "DATABASE_URL": "sqlite:///" + str(tmp_path / "migrated.db")}
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "check"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    engine = create_engine(env["DATABASE_URL"])
    tables = inspect(engine).get_table_names()
    assert {
        "users",
        "locations",
        "test_attempts",
        "test_results",
        "complaints",
        "timeline_events",
        "incidents",
        "notifications",
        "audit_events",
    } <= set(tables)
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "downgrade", "base"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "users" not in inspect(engine).get_table_names()
    engine.dispose()


def test_viewmodel_can_be_called_without_http_request(system):
    _, _, ids, factory = system
    with factory() as db:
        result = AuthViewModel.login(
            Credentials(email="alice@campus.edu", password="Password123!"), db
        )
        assert result["user"]["id"] == ids["alice"]
        assert "password_hash" not in result["user"]
        try:
            AuthViewModel.login(Credentials(email="alice@campus.edu", password="wrongpassword"), db)
        except DomainError as exc:
            assert exc.status_code == 401
        else:
            raise AssertionError("Invalid credentials accepted")
