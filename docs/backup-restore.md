# MoodFeed PostgreSQL Backup & Disaster Recovery Runbook

- **Standard:** Continuous Archiving & Point-In-Time Recovery (PITR)
- **Target Objectives:** RPO <= 15 minutes, RTO <= 30 minutes

---

## 1. Backup Strategy

1. **Full Database Dump:** Executed daily at 02:00 UTC via `pg_dump` with custom compressed format and AES-256 encryption.
2. **Continuous WAL Archiving:** PostgreSQL WAL logs shipped every 5 minutes to isolated encrypted storage.

---

## 2. Backup & Restore Scripts

### Executing a Backup:
```bash
# Set environment
export PGHOST=localhost PGPORT=5432 PGUSER=moodfeed_user PGDATABASE=moodfeed_db

# Create timestamped encrypted backup
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
pg_dump -Fc "$PGDATABASE" > "backups/moodfeed_backup_${TIMESTAMP}.dump"
```

### Executing a Restore Drill:
```bash
# 1. Stop web workers
# 2. Terminate active database connections
# 3. Restore schema and data
pg_restore --clean --if-exists -d "$PGDATABASE" "backups/moodfeed_backup_${TIMESTAMP}.dump"

# 4. Verify table row counts and integrity checks
python -m tests.test_production_persistence
```
