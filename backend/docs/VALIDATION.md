# Validation

Checked on 2026-10-01 with Python 3.12 and Node 24.

- `python -m pytest -q`: **15 passed**.
- `node --test integration/tests/*.test.mjs`: **6 passed**.
- `python -m ruff check .`: **passed**.
- Frozen migration upgrade, schema drift check and downgrade: passed on fresh SQLite databases.
- MVVM boundaries: thin normal API Views delegate, ViewModels do not import FastAPI/Starlette, an authentication command runs directly without an HTTP request.
- Real TCP integration: separate API/measurement subprocesses; supplied frontend measurement Model ran latency, download and server-confirmed upload, then saved a result through the API.

Functional coverage includes authentication/refresh/logout, role/campus scope, private complaint history, input validation, bounded transfers, token audience isolation, duplicate results/complaints, missing versus zero metrics, expiry, complaint assignment/resolution/reopening, incident independence/deduplication/recovery, maintenance suppression, stale data, threshold versions and filtered dashboard/analytics.

One dependency deprecation warning remains: the installed Starlette still supports httpx-based TestClient but recommends httpx2 for a future transition. It did not affect these checks.

Not validated here: Docker/actual PostgreSQL runtime, production ingress/HTTPS, campus bandwidth calibration, true browser/mobile UI or final deployment. PostgreSQL/Compose configuration is supplied for testing in your environment. The real TCP test used the shipped JavaScript measurement Model through Node fetch; browser/mobile calibration remains necessary.

No real campus measurements, private credentials or live user data are bundled. API examples use synthetic fixtures and placeholder tokens.
