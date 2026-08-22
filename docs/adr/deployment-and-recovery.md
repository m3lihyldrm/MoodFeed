# Architecture Decision Record: Deployment, Containerization & Disaster Recovery

- **Status:** Accepted / Implemented
- **Date:** 2026-08-22
- **Context:** Container packaging, immutable deployments, and backup verification.

---

## Decision

1. **Multi-Stage Docker Architecture:**
   - Builder stage creates Python wheels.
   - Runner stage executes on `python:3.11-slim` under non-root system user `appuser` (UID 10001).
   - Built-in HTTP health check verifying `/v1/system/health`.
2. **Local Staging Environment:**
   - `docker-compose.yml` orchestrating FastAPI `app`, PostgreSQL 16 `db` with schema auto-init, and Redis 7 `redis`.
3. **Backup & Recovery Strategy:**
   - Daily automated logical database backups (`scripts/backup.sh`) with compressed custom format.
   - Recovery runbook and drill script (`scripts/restore.sh`, `scripts/restore-drill.sh`) targeting RPO <= 15 min, RTO <= 30 min.

---

## Consequences

- Secure, reproducible container builds ready for staging.
- Clear operational recovery runbooks with measurable RTO/RPO objectives.
