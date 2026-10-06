# Person 2 — frontend handoff

## Own these files and screens

Build frontend Views: login, campus/location selection, speed-test progress/result/history, complaint form/history/detail, IT queue/assignment/investigation, dashboard/charts/heatmap, notifications, then administration/manager/maintenance screens. All screen state goes in ViewModels; all API/measurement access goes in Models. React components render state and call commands.

The backend and the frontend do not share a database connection. Use the documented HTTP contract. The backend owns authorization, scores, lifecycle validation and evidence rules. Your UI may hide inappropriate controls, but backend permission checks remain authoritative.

## Use the provided MVVM integration kit

1. Copy `integration/models` and `integration/viewmodels` into the frontend source tree. They are dependency-free ES modules usable with React/Vue/plain JavaScript. Node 22+ tests are optional.
2. Create one `CampusApi` per app session with the correct API URL. Create `AuthViewModel` with that API Model.
3. Load `/locations` and `/endpoints` for selectors. A paginated location response has `items`; do not treat it as a raw array. Locations already include health/read models.
4. Create `SpeedTestViewModel(api, new BrowserMeasurement())` and bind it to the speed-test View. `run(locationId, endpointId)` starts the session, measures on the device, saves results and maps them into the brief's display contract.
5. `cancel()` aborts transfers and records a cancelled attempt. `pendingSave` means measured data has not been saved. Show an explicit retry button calling `retrySave()`; do not rerun measurements when saving fails.
6. Use `ComplaintsViewModel` for listing, submission, detail, assignment and status updates. A failed submission retains its draft identifier for a safe retry; discard the draft before submitting a different complaint.
7. `DashboardViewModel.load(filters)` handles loading/errors and ignores outdated responses from earlier filter selections.
8. Notifications: load through the API Model, display unread records, mark read by ID. Keep polling modest and only while the page is visible.

`ReactBinding.example.jsx` shows `useSyncExternalStore` and a small speed-test View. It is an integration example, not a finished UI. Retain the user's explicit campus-Wi-Fi confirmation before starting a test.

## UI states to implement

- Loading, no records, success, failure, access denied and expired session.
- Test progress: starting → latency → download → upload → saving → finished; cancellation and save_pending.
- Partial results: show each missing metric as “Not measured.” Display zero as zero, not as missing.
- Insufficient score: “Insufficient data,” never a guessed score.
- Campus location with stale/unknown data: gray badge and timestamp/sample count.
- Suspected incident: explicitly say “Suspected”; do not show confirmed outage wording before IT confirmation.
- Internal notes: accessible only to IT roles; ordinary complaint detail responses omit them.
- Resolution: provide a picker for recent complete healthy verification-test IDs. Complaints require one; incidents require two independent users after monitoring begins.
- Offline complaint: save a local draft and label it “Not submitted.” Retry the same identifier only after reconnecting. Do not show successful submission before the API confirms it.

## Work split

| Person 1 — backend | Person 2 — frontend |
|---|---|
| Models, database/migrations, scoring and incident rules | UI components and page/navigation Views |
| Backend ViewModels and API/measurement Views | Observable frontend ViewModels and browser measurement integration |
| Roles, permissions, complaints, audit and recovery | Role-aware controls, error/loading/empty states |
| Dashboard/analytics/notifications contract | Cards, charts, heatmap and notification panel |
| Backend deployment and API explanation | Frontend deployment, screenshots, video and document assembly |

First integration checkpoint: log in, retrieve real locations, select one. Second: run a real device test, save once and show the score/history. Third: reporter submits a complaint, IT reviews/assigns/investigates, IT resolves manually without a verification test, reporter receives an in-app notification.

Use `docs/examples.json` as mock data while developing, and replace mock adapters with `CampusApi` for integration. Keep synthetic data visibly labeled. The UUIDs in example responses belong to test fixtures, not your installation.

For phones, use the API and measurement URLs reachable from that phone; `localhost` points to the phone itself. Serve the frontend over HTTPS for a realistic mobile deployment, configure CORS origins, and test on campus Wi-Fi. Device throughput/RTT depends on endpoint capacity, device conditions and HTTP overhead; compare with a trusted measurement under controlled conditions before claiming accuracy.
