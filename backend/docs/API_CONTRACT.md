# API contract — v1

The API base is `http://localhost:8000`; measurement traffic uses the endpoint `base_url` returned by `POST /test-sessions` (default `http://localhost:8001/measure`). Use JSON for ordinary requests and `application/octet-stream` for upload payloads.

## Shared rules

- IDs are UUID strings. `submission_id` is an 8–100-character unique client identifier (a UUID works).
- Authentication: `Authorization: Bearer <access_token>`. Measurements instead use the short-lived `measurement_token`.
- Metrics: Mbps for throughput, milliseconds for application RTT/jitter, scores from 0 to 100.
- Unavailable values are JSON `null`, never fabricated zeros. Packet loss is not measured or accepted in browser submissions.
- Status codes and status strings are lowercase. UI ViewModels translate labels for display.
- Datetimes use UTC ISO 8601 with `Z`; input dates must include an offset. `since` is inclusive; `until` is exclusive. Dashboard day boundaries use the campus timezone.
- Paginated lists return `{ "items": [], "total": 0, "limit": 50, "offset": 0 }`; max `limit` is 200. `/buildings`, `/endpoints`, `/auth/campuses` are small configuration lists returned as arrays.
- `/tests` defaults to personal history. IT can request `mine=false` to view its campus's tests. Complaints are automatically scoped to the current reporter unless the current user is IT/manager/admin.
- Errors: `{ "error": { "code": "422", "message": "..." } }`. Validation errors additionally provide `details` with field/message; they do not echo secret or private input values. Framework-level query errors on the measurement app can use FastAPI's `detail` list.
- Retry session creation with the same `submission_id`. Retry result save with the same session ID and exact outcome. Retry complaints with the same `submission_id` and exact fields. Different payloads using finalized IDs receive 409. Concurrent uniqueness conflicts receive 409; retry the same payload to retrieve the winning record.

`docs/openapi.json` contains current request schemas and routes. `docs/examples.json` contains actual synthetic request/response examples from this implementation; its UUIDs and tokens must be replaced with IDs/tokens from your running server.

## Authentication

`POST /auth/login`:

```json
{"email":"student@demo.campus","password":"your-generated-password"}
```

Response:

```json
{
  "user":{"id":"UUID","name":"Demo student","email":"student@demo.campus","role":"student","campus_id":"UUID","is_active":true,"created_at":"2026-10-01T05:00:00Z"},
  "access_token":"JWT","refresh_token":"OPAQUE_TOKEN","token_type":"bearer","expires_in":1800
}
```

`POST /auth/refresh` accepts `{"refresh_token":"..."}` and returns a fresh token pair. Old access/refresh credentials are revoked on rotation. `POST /auth/logout` revokes the current session. `GET /auth/me` returns the user. `POST /auth/register` takes `name`, `email`, `password`, `campus_id`; role is always student.

Role mapping: **student/staff** = regular reporters, **support** = IT, **manager** = operational oversight, **admin** = configuration. All five roles are restricted to their assigned campus. Use admin-created accounts for privileged roles.

## Start a device test

`POST /test-sessions`:

```json
{"location_id":"UUID","endpoint_id":"UUID","submission_id":"CLIENT_UUID","campus_wifi_confirmed":true}
```

Response includes:

```json
{
  "id":"TEST_SESSION_UUID","status":"created","location_id":"UUID","endpoint_id":"UUID",
  "expires_at":"2026-10-01T05:10:00Z","measurement_token":"JWT","base_url":"http://localhost:8001/measure",
  "limits":{"download_bytes":8388608,"upload_bytes":8388608,"session_bytes":67108864},
  "notice":"..."
}
```

Use `GET {base_url}/ping` repeatedly; measure full browser round trip including reading the response. Download from `GET {base_url}/download?bytes=N`. Upload binary data to `POST {base_url}/upload`; response confirms `received_bytes` and `server_receive_seconds`. Throughput uses browser-measured elapsed time and server-confirmed received bytes for uploads. Each transfer has a byte cap and each session a total reservation budget. Unknown-length uploads reserve their full configured upload cap. Failed/aborted transfers can consume reserved budget.

`POST /test-sessions/{id}/result` for completion:

```json
{"status":"completed","download_mbps":100,"upload_mbps":30,"latency_ms":15,"jitter_ms":2}
```

Upload metrics require a confirmed upload for this session. Browser-submitted values remain client-reported and validated for ranges, not independently attested. No upload sample is inferred just because a browser started uploading.

Partial example:

```json
{"status":"partial","download_mbps":12,"upload_mbps":null,"latency_ms":190,"reason":"Upload timed out"}
```

Failed/cancelled examples:

```json
{"status":"failed","reason":"Endpoint unreachable"}
```

```json
{"status":"cancelled","reason":"Cancelled by user"}
```

Response shape: `{ "attempt": <attempt>, "result": <result-or-null>, "duplicate": false }`. Test results contain `score`, `health`, raw metrics, `threshold_version`, `measurement_method`, `trust` and `explanation`. An attempt holds `status`, `location_id` and `finished_at`. One available core metric can be stored as a partial result but has no score; two metrics are required for scoring.

### Map to the brief's frontend contract

The integration helper `testPresentation()` produces:

```json
{
  "test_id":"UUID","location_id":"UUID",
  "download_mbps":100,"upload_mbps":30,"latency_ms":15,
  "packet_loss_percent":null,"health_score":100,"health_status":"Excellent",
  "outcome":"completed","tested_at":"2026-10-01T05:00:00Z","explanation":{}
}
```

| Frontend field | Raw API field |
|---|---|
| test_id | attempt.id |
| location_id | attempt.location_id |
| outcome | attempt.status |
| tested_at | attempt.finished_at, or attempt.created_at |
| health_score | result.score |
| health_status | Display label from result.health |
| packet_loss_percent | null (not measured) |

## Complaints

`POST /complaints`:

```json
{
  "location_id":"UUID","category":"slow_internet","description":"The connection is slow in the reading area.",
  "submission_id":"CLIENT_UUID","test_id":"OPTIONAL_TEST_UUID","occurred_at":"2026-10-01T05:00:00Z"
}
```

Omit `test_id` when no test is available. Evidence must belong to the reporter, match the location, be finalized and be less than 24 hours old. Allowed categories: `no_internet`, `slow_internet`, `high_ping`, `frequent_disconnection`, `weak_signal`, `service_unavailable`, `other`.

Response includes `id`, human reference `CMP-...`, `status`, location/user/evidence IDs and timestamps. `GET /complaints/{id}` adds chronological `events`; internal notes are omitted for regular users.

Lifecycle:

`submitted → reviewed → assigned → in_progress → resolved → closed`

- Review: `POST /complaints/{id}/transitions` with `{"status":"reviewed","note":"Reviewed by IT"}`.
- Assign: `PATCH /complaints/{id}/assignment` with `{"assignee_id":"IT_USER_UUID","note":"Assigned to IT"}`.
- Start: transition to `in_progress`.
- Note: `POST /complaints/{id}/notes` with `{"note":"...","visibility":"public"}` or `internal` (IT only).
- Resolve: authorized IT can transition directly to `status=resolved` from any complaint status. Verification tests are not required. The canonical transition accepts a note; the dashboard provides a default if its optional note is empty. Resolution is recorded as manual with the acting staff member and timestamp. Incident recovery rules remain unchanged.
- Reporter or IT may transition resolved/closed complaints to `reopened`; IT then resumes `in_progress`.
- IT may set `awaiting_user`/`awaiting_external` while investigating and later resume.

Assigning requires an active support/manager/admin in the same campus. Status changes and notes are preserved, never overwritten.

## Incidents / verified recovery

`GET /incidents` lists campus incidents; reporter-facing records omit private investigation/evidence fields. Detection creates **suspected** incidents, never confirmed outages, when enough independent reports correlate and an operator-approved endpoint has a recent authenticated probe. Default: 3 independent users, score below 50, 60-minute window. No-internet complaints can also contribute. Scheduled maintenance suppresses new detection.

`PATCH /incidents/{id}/assignment`: `{"owner_id":"IT_UUID","severity":"high"}`.

`POST /incidents/{id}/transitions`: status/note with optional evidence, root cause/action.

Lifecycle: `suspected → confirmed → investigating → monitoring_recovery → resolved`. A suspected incident may be `dismissed`; resolved/dismissed incidents may reopen if no other incident is active at the location.

Resolution requires an owner, root cause (or explicit `not confirmed`), action taken, and at least **two independent users'** recent complete healthy verification tests **after entering monitoring_recovery**. The configured default recovery score is 75. Complaints are resolved individually; resolving an incident does not silently resolve all linked complaints.

## Dashboard, filters and analytics

`GET /dashboard`: counts, range-average metrics, today's metrics, location-health records, personal counters, timestamp/timezone. Includes tests today, average download/upload/application RTT, poor locations, open/resolved complaints, active incidents, tests/complaints by location and latest location result.

Filters: `location_id`, `building_id`, `since`, `until`, `network_status`, `category`, `complaint_status`. Network status filters locations by **current recent** health/operational status; date filters affect **historical tests and complaint counts**, not the current health window. This distinction is intentional.

`GET /analytics` (IT/manager/admin): hourly/daily series, building comparisons, categories/statuses, resolution times, workload, recurring-problem ranking, exploratory trends and a rule-based summary. `GET /reports/tests.csv` exports filtered tests.

Scored location health uses each user's **latest scored/partial observation in the recent window**, then takes a median of scores. Repeat tests from one user do not increase the independent-user confidence count. Location records show `sample_count`, `independent_users`, `scored_users`, `confidence`, `last_updated`, `operational_status`, score band and average/median metrics. Labels: `unknown`, `insufficient_data`, `low_confidence`, `current`, `stale`, `suspected_outage`, `active_incident`, `maintenance`. Health bands: excellent/good/fair/poor/critical.

## Administration / notices

Admin: `POST /admin/buildings`, `POST /admin/locations`, `PATCH /admin/locations/{id}`, `GET/POST /admin/users`, `PATCH /admin/users/{id}`, `GET/POST /admin/thresholds`, `POST /admin/endpoints`, `PATCH /admin/endpoints/{id}`, `GET /admin/audit`.

Campus, initial admin and initial thresholds are created through the explicit bootstrap command. Threshold updates create a new immutable version; stored old scores retain their original version.

IT: `GET/POST /maintenance`, `POST /maintenance/{id}/cancel`. Schedule includes `location_id`, `description`, `starts_at`, `ends_at` (timezone-aware inputs).

All users: `GET /notifications?unread_only=true`, `PATCH /notifications/{id}/read`. Notifications are durable in-app records; no email/SMS delivery is claimed. Your frontend can poll notifications/dashboard every 15–30 seconds while visible; use backoff on errors.

### Dashboard internet tests

`POST /workspace/internet-test-sessions` accepts `location_id` and an idempotent `submission_id`. It returns `transport=cloudflare` and the fixed public provider URL. The browser measures directly against Cloudflare without campus tokens, then saves its browser-reported metrics through the canonical result endpoint. A fresh completed, partial or failed test can be attached to a complaint. Campus measurement upload receipts remain required for campus endpoints.
