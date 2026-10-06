# Deployment and operational setup

## Environments

Local development uses SQLite. PostgreSQL is required by production validation. All services need the same database and `SECRET_KEY`. Configure real HTTPS origins; never publish `.env` or passwords in a repository. Bootstrap is explicit and prompts for a password.

Docker Compose is a provided deployment configuration. It has not been executed in this workspace because Docker/PostgreSQL are unavailable here. Run it and the acceptance workflow in your environment before your demo. Locally exercised tests use SQLite and real HTTP handlers.

## Production configuration

Set `ENVIRONMENT=production`, `DATABASE_URL=postgresql+psycopg://...`, random `SECRET_KEY` of 32+ characters, `MEASUREMENT_BASE_URL=https://measurement.your-domain/measure`, and exact `CORS_ORIGINS` JSON. Example secret generation:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Put API and measurement services behind HTTPS reverse proxies. Disable buffering/caching/compression on measurement routes, retain byte lengths, set upload/body/time limits, and keep transfers on a separate service/path/capacity budget. Use one measurement worker initially; its transfer semaphore is process-local. Configure shared ingress rate/concurrency limits for multiple instances, and trusted forwarding rules. The API's built-in client-IP limiter is a local development guard; it is not a distributed limiter or a spoof-resistant proxy configuration.

Do not configure gzip middleware for `/measure`. Proxy/CDN compression, queuing and caching distort measurements. The upload rate helper measures server-confirmed bytes over end-to-end request time; server_receive_seconds is diagnostic, not the authoritative device throughput.

## Database lifecycle

```bash
python -m alembic upgrade head
python -m app.bootstrap --email admin@campus.edu --campus "Real Campus"
```

Configure actual buildings/locations and users through administration. The frozen migration manifest is independent of live application models. After future schema changes create a new revision with `python -m alembic revision --autogenerate -m "description"`, inspect it, test upgrade/rollback on a copy and deploy with a backup. Never modify the applied initial migration in an existing deployment.

For Docker: `docker compose exec api python -m app.bootstrap ...`. Demo accounts/configuration are for local demonstration only. Public registration has no email verification or institution-domain allowlist; add campus SSO or registration approval/domain verification before opening campus enrollment widely.

## Endpoint health and limits

Start with bounded transfers (8 MiB each way, 64 MiB per session, eight concurrent transfers). Calibrate these against campus capacity. Reachable does not prove adequate capacity: an operator must confirm endpoint health. The incident rule requires both this confirmation and a recent authenticated probe. A failed test does not directly create a confirmed outage.

Optional automatic infrastructure/endpoint monitoring is not implemented. To monitor idle campuses continuously, integrate approved scheduled probes later. Crowdsourced observations do not guarantee continuous coverage.

## Worker / notifications

Run `python -m app.worker` under a process supervisor. It expires unsubmitted sessions, scans incident rules and deduplicates maintenance-end notices. Request-triggered scoring and detection occur immediately; the worker handles periodic scans. Run one worker initially; PostgreSQL location locks and uniqueness keys protect deduplication, but deployment concurrency still needs load testing.

In-app notifications are created transactionally and are immediately available via `/notifications`. No external notification channels or retry adapters are implemented. Email/SMS requires an actual provider/outbox integration; do not relabel in-app availability as external delivery.

## Logs / readiness

Check `/health/live`, `/health/ready` and measurement `/health/live`. API readiness checks database connectivity and schema. Readiness is not proof of seeded campus configuration, worker activity or endpoint capacity. Monitor all three services separately and measure upload/download behavior from actual client devices. Errors avoid logging payloads/credentials; add structured operational logging and retention policies appropriate to the campus before production.

## Backup / restore

PostgreSQL: use managed backups or schedule `pg_dump`, protect backups and test restoring to a separate database with `pg_restore` before switching connection settings. SQLite demo backup: stop all three processes and copy `campus.db`; never copy a live database/WAL pair without SQLite's backup API. Retention/deletion policies are deployment decisions; this code does not automatically purge evidence/history.

## Acceptance run

Run login → location → device measurements → saved score/history → complaint → IT review/assignment/investigation → repair → independent verification → complaint/incident resolution → reporter notification → dashboard/analytics. Repeat with partial/cancelled tests, endpoint failure, duplicate submissions, unauthorized users, stale data, maintenance and reopened complaints.

Check real-device calibration and concurrent endpoint capacity on campus. SQLite/handler integration tests do not establish measurement accuracy, PostgreSQL behavior under load or readiness of the final frontend.
