# MoodFeed Data Retention & Disposal Policy

- **Version:** 1.0.0
- **Scope:** All production databases, caches, logs, and export artifacts.

---

## 1. Retention Schedule

| Category | Retention Window | Purge Trigger | Mechanism |
| :--- | :--- | :--- | :--- |
| **Active User Account Data** | Lifetime of account | User deletion request | Cascade delete + anonymization job |
| **Inactive Account Data** | 24 months of total inactivity | Automated lifecycle rule | Email notification + 30-day grace purge |
| **Session & Refresh Tokens** | 14 days | Expiry or logout | Daily scheduled cleanup job |
| **Audit Logs** | 12 months | Age > 365 days | Rolling partition drop |
| **Application & Error Logs** | 30 days | Age > 30 days | S3 lifecycle / Logstash rotation |
| **Export Download Artifacts** | 15 minutes (temporary) | Expired signed URL | Immediate file system / blob delete |
| **Pilot Evaluation Data** | 60 days post-study | Study completion | Explicit research database truncation |

---

## 2. Automated Purging Workflow

1. **Daily Maintenance Cron:** Runs at `03:00 UTC` executing `retention_cleanup` background task.
2. **Hard-Delete vs Soft-Delete:** Account deletion marks `deleted_at = NOW()`. After 30 days grace, all user preferences, bookmarks, and sessions are permanently scrubbed with zero residual backups past the 14-day PITR retention window.
