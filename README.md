# CampusNet — Smart Campus Wi-Fi Monitoring

Integrated React dashboard and Python backend for student, IT support, manager and administrator workflows. The existing visual theme and layout are retained. Live mode uses authenticated server records; it does not load demo data when the server is unavailable.

## Requirements

- Node.js 22.13 or newer and npm.
- Python 3.12 or newer.
- Four local terminals for the frontend, API, measurement service and worker.

## First setup — Windows PowerShell

Open a terminal in the extracted `smart-campus` folder:

```powershell
npm ci
Copy-Item .env.example .env.local
py -3.12 -m venv backend/.venv
backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
Set-Location backend
Copy-Item .env.example .env
.venv/Scripts/python.exe -m alembic upgrade head
.venv/Scripts/python.exe -m app.bootstrap --email your-admin@muet.edu.pk --campus "Mehran University of Engineering and Technology" --demo-locations
```

Bootstrap prompts for an administrator password of at least 10 characters. It creates the campus, initial administrator, threshold configuration, measurement endpoint and optional placeholder locations. It never creates fake measurement history. Use Locations in the administrator dashboard to replace placeholder names and place actual campus pins. The map defaults to MUET, Jamshoro; its center is not a building survey.

If upgrading an existing backend database, back it up, configure its `DATABASE_URL`, run `alembic upgrade head`, and sign in with existing accounts. Do not bootstrap a second campus unless intended.

## Run — separate terminals

All backend commands run from the `backend` folder, using the same `.env` and database:

```powershell
# Terminal 1: backend API
.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

```powershell
# Terminal 2: browser measurement service
.venv/Scripts/python.exe -m uvicorn app.measurement:app --host 127.0.0.1 --port 8001
```

```powershell
# Terminal 3: incident detection and expired-session processing
.venv/Scripts/python.exe -m app.worker
```

```powershell
# Terminal 4: frontend, from the smart-campus root folder
npm run dev
```

Open `http://127.0.0.1:5173`. The Vite development proxy forwards `/api` to port 8000 and `/measure` to port 8001. Sign in with the administrator created above. Students can create accounts through the existing sign-up page; administrators can then change their roles to IT Support or Manager in Users. If there is more than one campus, set `VITE_CAMPUS_ID` in the frontend `.env.local` to the campus ID printed by bootstrap and restart Vite.

Swagger API documentation is available at `http://127.0.0.1:8000/docs`. Initial endpoint health is deliberately unconfirmed. After testing endpoint reachability and capacity, an administrator can enable `operator_healthy` through `PATCH /admin/endpoints/{id}` in Swagger; this is required for reliable automatic incident detection.

## What is connected

- Authenticated role-specific dashboards with server-enforced campus scope.
- Real browser-to-endpoint RTT, download and upload measurements, scoring and history.
- Complaints with map-selected locations, optional test attachments, assignment and investigation notes.
- Manual IT complaint resolution from any status, with optional resolution notes and an audit trail.
- Custom map locations and administrator pin/name editing.
- Persistent maintenance notes, support activity and recurring-problem reporting.
- Account roles, activation, role capabilities and versioned health thresholds.
- Persistent user notifications, read state, error feedback and recorded analytics.

See [INTEGRATION.md](INTEGRATION.md) for architecture, schema changes, validation and limitations.

## Validate

```powershell
# Project root: TypeScript and frontend production build
npm run build
npm test
# backend folder: backend tests, migration drift and integration coverage
.venv/Scripts/python.exe -m pytest tests -q
```

The integrated build and all 18 backend tests pass. Live browser verification used an isolated synthetic database; its users, credentials and records are not packaged.

## Deployment and measurement limits

Deploy the frontend build with a reverse proxy for `/api`, or set `VITE_API_URL` before building. The measurement endpoint returned by the API must be reachable from the user's device. Configure HTTPS, CORS origins, production secrets, PostgreSQL, backups and shared rate limiting. See [backend/docs/DEPLOYMENT.md](backend/docs/DEPLOYMENT.md).

The dashboard measures the device’s active internet connection directly against Cloudflare. Each full test transfers about 26 MiB and never proxies speed traffic through localhost. The optional canonical campus measurement API still measures its configured endpoint. HTTP tests cannot measure packet loss or Wi-Fi signal, and selecting a campus location does not prove Wi-Fi association. Campus-wide history omits user identities. The supplied backend has no email password-recovery service; the existing recovery form reports this limitation. Notifications are in-app and refresh every 30 seconds.

`VITE_USE_BACKEND=false` explicitly restores the original local demo workspace for demonstrations. It should not be enabled for live campus operations.

The ZIP excludes dependencies, virtual environments, caches, credentials and databases. Install dependencies with the commands above.

## Administrator AI features

Set `GEMINI_API_KEY` in the private `backend/.env` file, then restart the API. The delivery contains only an empty example setting. The key must never be placed in frontend variables. `GEMINI_MODEL` defaults to `gemini-3.8-flash`; use a generateContent model available to your Google project. Provider requests have a bounded timeout.

New complaints are classified automatically into slow internet, high latency, frequent disconnection, no internet, weak signal, service unavailable or other. Gemini suggestions with confidence at least 0.65 are applied automatically; lower-confidence suggestions remain reviewable. Administrators can classify older complaints individually, inspect the reasoning, and apply a suggested category. The original submitted category and analysis are audited, and retries do not trigger duplicate analysis.

The AI Network Summary page generates IT observations and suggested checks for the last 24 hours, 3 days or 7 days. Only computed campus aggregates are sent for summaries; user names, emails and raw complaint text are excluded. Classification sends the complaint description after common email and phone patterns are redacted. Do not put sensitive information in complaint descriptions. Model confidence is an estimate and recommendations require IT review.

When Google is unavailable, classification provides explicitly labelled keyword suggestions and summaries provide a factual data summary. These fallbacks do not claim to be Gemini outputs. Empty periods show insufficient evidence. Analyses and the latest summary persist in the audit store; endpoints enforce administrator access and campus scope. Summary generation has a 30-second cooldown.
