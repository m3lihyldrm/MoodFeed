# MoodFeed Disaster Recovery & Business Continuity Plan

- **Recovery Point Objective (RPO):** <= 15 minutes
- **Recovery Time Objective (RTO):** <= 30 minutes

---

## 1. Disaster Scenarios & Recovery Procedures

### Scenario A: Database Corruption or Data Loss
1. Provision clean PostgreSQL 16 instance.
2. Apply latest compressed backup from backup storage:
   ```bash
   bash scripts/restore.sh backups/latest_backup.dump
   ```
3. Run test suite to verify table row counts and integrity constraints:
   ```bash
   python -m pytest tests/test_production_persistence.py
   ```

### Scenario B: Complete Server Outage
1. Deploy Docker Compose or Kubernetes manifests to standby infrastructure.
2. Populate environment variables from secure secret manager (Vault / AWS SSM).
3. Verify `/v1/system/readiness` and `/v1/system/liveness` probes.

---

## 2. Quarterly Drill Requirement

- Mandatory quarterly restore drills must be performed using `scripts/restore-drill.sh` to measure actual RTO against staging infrastructure.
