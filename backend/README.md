# Smart Campus Wi-Fi Monitoring — MVVM Backend

Runnable Python backend for the supplied campus Wi-Fi project. Includes real device-to-server measurement endpoints, scoring, complaint handling, incident detection, analytics and an MVVM integration kit for your frontend partner.

**Stack:** Python 3.12+, FastAPI, SQLAlchemy, Alembic, SQLite for local development, PostgreSQL for deployment. API: port **8000**. Separate measurement service: port **8001**. The integrated React frontend is in the parent folder; see its README and INTEGRATION.md.

## Start on Windows (PowerShell)

Extract the ZIP, then open a terminal in `smart-campus-backend`:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m app.bootstrap --email admin@campus.edu --campus "My Campus" --demo-locations
```

Bootstrap asks for your administrator password and prints the new campus ID. It creates an administrator, initial scoring configuration, test endpoint and optional **demo location configuration**. It does not invent speed-test records.

Run each process in its own terminal, from the same project directory:

```powershell
# Terminal 1 — API
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

```powershell
# Terminal 2 — measurement endpoint
.\.venv\Scripts\python.exe -m uvicorn app.measurement:app --host 0.0.0.0 --port 8001
```

```powershell
# Terminal 3 — periodic rules and expiry
.\.venv\Scripts\python.exe -m app.worker
```

Open http://localhost:8000/docs for interactive API documentation. Sign in through `POST /auth/login`; use the returned **access_token** in Swagger's **Authorize** box. Login accepts JSON with `email` and `password`. Swagger does not automatically sign you in.

Optional student/support/manager demo accounts:

```powershell
.\.venv\Scripts\python.exe -m app.demo --campus-id YOUR_CAMPUS_ID
```

This prints random demo passwords once; it refuses to run in production. For actual accounts use `POST /admin/users`; public registration always creates a student.

## Start on Linux/macOS

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
.venv/bin/python -m alembic upgrade head
.venv/bin/python -m app.bootstrap --email admin@campus.edu --campus "My Campus" --demo-locations
.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Run `app.measurement:app` on port 8001 and `python -m app.worker` in separate terminals using the same virtual environment and directory.

## MVVM structure

| Layer | Files | Responsibility |
|---|---|---|
| Model | `app/models/entities.py`, `contracts.py`, `network.py`, `measurement.py`, `reporting.py` | Persistent data, validation contracts, scoring, incident rules, measurements and aggregates |
| ViewModel | `app/viewmodels/` | Use-case commands, permission boundaries, lifecycle decisions, presentation-ready responses |
| View | `app/views/`, `app/measurement.py` | Thin FastAPI adapters for HTTP input/output |
| Infrastructure | `app/db.py`, `security.py`, `config.py`, `common.py`, `errors.py` | Database transactions, tokens, configuration and reusable access/serialization helpers |
| Frontend Model | `integration/models/` | API requests and measurements running on the user's device |
| Frontend ViewModel | `integration/viewmodels/` | Observable state, commands, cancellation, safe retries and data mapping |
| Frontend View | Partner's screens; `integration/ReactBinding.example.jsx` | Render state and invoke ViewModel commands |

On a backend, MVVM is adapted to request/response APIs: an API View receives a command and delegates to a ViewModel, which uses the Model and returns a read model. Browser ViewModels implement observable state binding. Backend ViewModels have no FastAPI/Starlette imports and can be tested without HTTP requests.

`app/models/__init__.py` exports the entities. `app/schemas.py`, `services.py` and `reporting.py` are compatibility import facades; implementations live in the Model folder.

## Implemented features

- Argon2 password hashing, JWT access tokens, rotating refresh sessions and server-side logout/revocation.
- Student, staff, support, manager and administrator roles with campus scoping.
- Buildings, floors and locations; soft deactivation keeps historical references intact.
- Authorized, expiring speed-test sessions with retry identifiers.
- Uncached download data, bounded streaming uploads with server-confirmed byte receipts, and HTTP application RTT probes.
- Complete, partial, failed and cancelled outcomes; missing values stay `null`.
- Explainable scoring with versioned thresholds, subscores and measurement coverage.
- Latest-per-user location aggregation, confidence/sample counts, unknown/stale/maintenance labels.
- Complaints, assignment, valid transitions, public/internal notes, evidence ownership and complete history.
- Deduplicated suspected incidents from independent reports, operator-confirmed endpoint health and maintenance suppression.
- Investigation, incident ownership, recovery verification and reopening.
- Dashboards, date/building/location/status filters, hourly/daily analytics, comparisons, workload and CSV export.
- In-app notifications for complaints, assignments, poor observations, incidents, recovery and maintenance; read indicators.
- Audit records, consistent errors, payload limits, local request limits and measurement concurrency/byte budgets.
- Frozen initial migration, bootstrap/demo commands, Docker Compose and tests.

## Your partner's handoff

Give Person 2 the `integration/` and `docs/` folders. Start with [API_CONTRACT.md](docs/API_CONTRACT.md), [PARTNER_HANDOFF.md](docs/PARTNER_HANDOFF.md), `docs/examples.json` and `docs/openapi.json`.

Copy the integration kit into the frontend. Create one shared `CampusApi` instance, log in, then bind screen state to the provided ViewModels. Browser measurements use a separate **measurement token**, not the API access token. `testPresentation()` maps raw API fields to the sample contract in your brief: `health_score`, `health_status`, `packet_loss_percent`, `outcome`, `tested_at`.

## Important setup details

- For a phone/laptop on your LAN, replace `localhost` in `MEASUREMENT_BASE_URL` with your computer's reachable LAN IP, e.g. `http://192.168.1.25:8001/measure`. Also update the seeded endpoint through a new endpoint record, and pass its ID to test creation. Your frontend API base URL must use that reachable IP too. CORS must list the actual frontend origins. Restart services after environment changes.
- Do not label the local development server as an internet speed test. A campus endpoint measures the campus path; an external deployment measures the internet path. Configure `Endpoint.scope` accordingly.
- Initial `operator_healthy=false` deliberately prevents automatic incident detection until IT checks endpoint capacity/reachability and enables it with `PATCH /admin/endpoints/{id}`. A recent authenticated ping is also required.
- Separate API and measurement processes share the same database, secret and configuration. One measurement process has eight transfer slots by default; multiple processes multiply that cap. Use ingress limits for a shared cap at scale.
- Tokens are held in memory by the integration client. Closing/reloading the page requires signing in again unless your partner implements a secure persistence/session strategy.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
node --test integration/tests/*.test.mjs
```

Tests cover the complete student-to-IT workflow, permissions, privacy, retries, token isolation/rotation, server upload confirmation, partial/failed results, incidents, maintenance, scoring versions, dashboard filters, migrations and MVVM boundaries. Node 22+ is needed only for the integration-kit tests, not for the Python backend.

## PostgreSQL / Docker

Copy `.env.example` to `.env`, set a random `POSTGRES_PASSWORD`, then:

```bash
docker compose up --build -d
docker compose exec api python -m app.bootstrap --email admin@campus.edu --campus "My Campus" --demo-locations
```

Compose starts PostgreSQL, runs migrations once, then starts API, measurement and worker. For an existing remote PostgreSQL server, use `DATABASE_URL=postgresql+psycopg://...` and run the same migration/launch commands directly. See [DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Limits and remaining deployment work

This is an implemented backend and integration kit, not a deployed campus installation. You must configure real locations, users, HTTPS domains, database credentials and endpoint capacity, and verify the integrated UI against your deployment. SQLite workflows and migration tests are exercised locally; Docker/PostgreSQL and real campus-device calibration require testing in your deployment environment.

Packet loss, SSID/signal extraction, continuous infrastructure probes, email/SMS, SSO, machine-learning prediction and traffic telemetry are not implemented. Notifications are persistent **in-app** records. Intelligence is explicitly rule-based. Browser measurements are application-level throughput and RTT, with client-reported locations and metrics; they do not independently prove equipment failure.

## Integrated dashboard updates

The React dashboard now runs bounded internet tests directly from the browser against Cloudflare rather than the local measurement server. The campus endpoint API remains supported. Complaint submission runs and attaches a fresh test when enabled, and IT can resolve complaints manually without verification measurements. See the parent README and INTEGRATION.md for the current dashboard behavior. Incident resolution still requires its original verification evidence.
