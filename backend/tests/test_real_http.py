"""Real TCP API + measurement servers and the shipped device measurement Model."""

import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
import httpx
import pytest

ROOT = Path(__file__).resolve().parents[1]


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_real_tcp_measurement_with_frontend_model(system):
    if not shutil.which("node"):
        pytest.skip("Node is needed only for the optional browser-model TCP test")
    _, _, ids, factory = system
    with factory() as db:
        url = str(db.get_bind().url)
    api_port, measure_port = free_port(), free_port()
    env = {
        **os.environ,
        "DATABASE_URL": url,
        "MAX_DOWNLOAD_BYTES": "65536",
        "MAX_UPLOAD_BYTES": "65536",
    }
    procs = []
    try:
        for target, port in [("app.main:app", api_port), ("app.measurement:app", measure_port)]:
            procs.append(
                subprocess.Popen(
                    [
                        sys.executable,
                        "-m",
                        "uvicorn",
                        target,
                        "--host",
                        "127.0.0.1",
                        "--port",
                        str(port),
                        "--log-level",
                        "error",
                    ],
                    cwd=ROOT,
                    env=env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                )
            )
        with httpx.Client(timeout=5, trust_env=False) as client:
            for port in (api_port, measure_port):
                for _ in range(70):
                    try:
                        if client.get(f"http://127.0.0.1:{port}/health/live").status_code == 200:
                            break
                    except httpx.HTTPError:
                        pass
                    time.sleep(0.1)
                else:
                    raise AssertionError("Server did not start")
            token = client.post(
                f"http://127.0.0.1:{api_port}/auth/login",
                json={"email": "alice@campus.edu", "password": "Password123!"},
            ).json()["access_token"]
            headers = {"Authorization": "Bearer " + token}
            response = client.post(
                f"http://127.0.0.1:{api_port}/test-sessions",
                headers=headers,
                json={
                    "location_id": ids["location"],
                    "endpoint_id": ids["endpoint"],
                    "submission_id": "real-http-0001",
                    "campus_wifi_confirmed": True,
                },
            )
            assert response.status_code == 201, response.text
            session = response.json()
            session["base_url"] = f"http://127.0.0.1:{measure_port}/measure"
            script = "import {BrowserMeasurement} from './integration/models/BrowserMeasurement.mjs'; const s=JSON.parse(process.env.CAMPUS_TEST_SESSION); console.log(JSON.stringify(await new BrowserMeasurement().measure(s)));"
            result = subprocess.run(
                ["node", "--input-type=module", "-e", script],
                cwd=ROOT,
                env={**os.environ, "CAMPUS_TEST_SESSION": json.dumps(session)},
                capture_output=True,
                text=True,
                timeout=40,
            )
            assert result.returncode == 0, result.stderr
            outcome = json.loads(result.stdout)
            assert outcome["status"] == "completed", outcome
            assert (
                outcome["download_mbps"] > 0
                and outcome["upload_mbps"] > 0
                and outcome["latency_ms"] > 0
            )
            saved = client.post(
                f"http://127.0.0.1:{api_port}/test-sessions/{session['id']}/result",
                headers=headers,
                json=outcome,
            )
            assert saved.status_code == 200, saved.text
            assert saved.json()["attempt"]["upload_confirmed_bytes"] == 65536
            assert saved.json()["result"]["packet_loss_pct"] is None
    finally:
        for proc in procs:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
