# MoodFeed Deployment & Release Management Guide

- **Environments:** Development, Staging, Production
- **Strategy:** Immutable Container Images, Zero-Downtime Blue/Green Rolling Deployments

---

## 1. Local Staging Spin-Up
```bash
docker-compose up -d --build
# Verify health probes
curl -f http://localhost:8000/v1/system/health
curl -f http://localhost:8000/v1/system/readiness
```

---

## 2. Release Rollback Runbook

If a regression or critical vulnerability is detected post-deployment:
1. Revert container tag in deployment manifest to previous stable hash (`v1.0.0` -> `v0.9.9`).
2. If database schema migration was applied, execute corresponding down migration:
   ```bash
   python -m alembic downgrade -1
   ```
3. Trigger canary health probe check and purge Redis feed cache.
4. Notify incident response team and record post-mortem.
