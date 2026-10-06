# Backend integration

The original React screens, component styling, logo, maps and navigation are retained. Frontend actions now use authenticated FastAPI requests. Demo storage is available only with an explicit `VITE_USE_BACKEND=false`; live mode never silently falls back to sample records.

## Responsibilities

| Layer | Files | Responsibility |
| --- | --- | --- |
| React Views | `src/views`, `src/auth/views` | Existing forms, tables, maps and feedback |
| Frontend ViewModels | `src/viewmodels/useLiveCampusViewModel.ts`, `src/auth/viewmodels` | Load server state, orchestrate requests, handle errors and refresh views |
| Frontend Models/services | `src/models`, `src/services/backendClient.ts`, `src/services/browserMeasurement.ts` | Data contracts, authenticated HTTP and bounded browser measurements |
| Backend Views | `backend/app/views` | API routes and request dependencies |
| Backend ViewModels | `backend/app/viewmodels` | Authorization-aware use cases and complaint transitions |
| Backend Models | `backend/app/models` | Persistent entities, scoring, reporting and incident rules |
| Database | `backend/migrations/versions` | Versioned schema upgrades |

## Feature coverage

- Login, registration and restored sessions use the API; registration creates students only. Server account roles determine the workspace. Changing a role or disabling an account revokes its sessions.
- Student tests persist measured RTT, upload, download, outcome and score. Personal test history and deidentified campus observations come from the database.
- Complaint submission persists its selected location, optional associated test and reference. IT can assign, investigate and add notes. The dashboard adapter applies multi-step updates within one database transaction.
- IT can manually resolve complaints from any status without verification measurements. Resolution records the actor and time; notes are optional in the dashboard. Incident recovery verification remains separate.
- Custom locations persist names and map coordinates. Only administrators can edit existing campus locations. Coordinates must be finite, paired and within latitude/longitude bounds.
- Maintenance notes persist author, location and time and appear in support activity. Scheduled maintenance remains available through the canonical API.
- Manager connections, recurring complaint counts, activity and charts use server records. Charts aggregate actual samples instead of generating artificial trends.
- Administrator account management, campus location editing, role capabilities and versioned thresholds are wired to server writes. Self-demotion and self-deactivation are protected.
- Complaint and maintenance notifications persist per user. Immediate feedback confirms successful writes; failures retain the form. Notifications refresh every 30 seconds and read state is stored on the server.

## Added API and schema

Migration `0002_dashboard_features` adds `locations.latitude`, `locations.longitude`, `locations.user_reported`, `role_policies` and `maintenance_notes`. It does not modify the frozen initial migration or seed fabricated test results. Back up an existing database before upgrading.

The `/workspace` adapter returns the existing dashboard data shape. Additional endpoints create custom locations, edit admin locations, add maintenance notes, change role policies, list eligible assignees and atomically update complaints. Existing canonical endpoints remain available. Both paths enforce authenticated campus scope and applicable permissions.

## Verification

The integrated project passes the TypeScript/Vite production build and all 18 backend tests. Added tests cover custom coordinates, campus boundaries, permission revocation, maintenance notes, transactional complaint rollback, manual complaint resolution, notifications and deidentified campus history. Existing tests cover the original architecture, migrations, auth and measurement workflows.

Live browser verification used an isolated synthetic database and separate student, support and administrator accounts. Student login, a real browser-to-local-server measurement, persisted complaint submission, IT assignment and a persisted maintenance note were exercised. The updated dashboard uses direct browser-to-Cloudflare measurements. A fresh test runs and is attached before a complaint is sent when its attachment option is enabled. Test credentials and the verification database are excluded from the delivery.

## Operational limits

The existing forgot-password screen has no email recovery service in the supplied backend; it remains explicit about this limitation. No email is sent. Notifications are in-app, not push notifications. HTTP measurements do not measure RF signal, ICMP ping or packet loss, and do not prove the device is on campus Wi-Fi. A chosen map location is user-reported. Campus identity and actual building pins must be configured by your administrator.

The API uses request timeouts and professional feedback, but cannot submit while fully offline. A timeout after a write may mean the server saved it; refresh and inspect the list before submitting again. Production requires HTTPS, a non-development secret, actual measurement endpoint configuration, database backups, shared rate limits and deployment testing. See `backend/docs/DEPLOYMENT.md`.

## Internet measurement correction

The dashboard now uses `/workspace/internet-test-sessions` to register a fixed Cloudflare internet endpoint, then performs latency and bounded upload/download transfers directly from the browser. Campus credentials are never sent to Cloudflare. Results remain browser-reported; upload receipt requirements are retained for the canonical campus endpoint and explicitly bypassed only for the fixed external provider. Three frontend regression tests cover remote routing, credential isolation, unreachable endpoints and cancellation. Complaints can include a completed, partial or failed fresh test; unavailable metrics remain unknown.

## Administrator AI integration

The server-only provider is `backend/app/models/gemini.py`. AI orchestration and scoped aggregation live in `backend/app/viewmodels/ai.py`, with thin routes in `backend/app/views/ai.py`. React uses `useAdminAIViewModel.ts` and `AdminAIViews.tsx` without embedding credentials. `/admin/ai` exposes classifications and the latest persisted summary. New complaint creation calls the classifier before notification; idempotent retries compare the original submitted category.

AI audit records use the existing audit JSON schema, so this feature requires no additional database migration. The provided key is configured only in the local backend environment and excluded from the distribution. Each classification or summary can incur Google API usage. Failure messages hide provider error bodies and secrets; keyword and factual fallbacks are clearly marked.

Verification: 23 backend tests pass, including auto-classification, retry idempotency, fallback review, administrator and cross-campus boundaries, summary privacy, persistence and cooldown, and server-only key handling. The TypeScript/Vite production build passes.
