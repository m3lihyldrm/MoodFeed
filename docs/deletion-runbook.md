# MoodFeed Data Subject Deletion Runbook (GDPR Art. 17 & KVKK Madde 11)

- **Objective:** Operational procedure for executing user account and data deletion requests.

---

## 1. Automated Deletion Path (Self-Service)

1. User invokes `POST /v1/privacy/data/deletion` with valid session authentication.
2. System immediately revokes all active session tokens and refresh families (`sessions.is_revoked = TRUE`).
3. User record is soft-deleted (`users.deleted_at = NOW()`, `users.is_active = FALSE`).
4. Associated bookmarks (`saved_items`), mute rules (`muted_sources`, `muted_categories`), and preferences are deleted in cascade.
5. An audit event `USER_DELETION_REQUESTED` is recorded with anonymized metadata.
6. After 30 days, the scheduled deletion worker hard-deletes the user identity from PostgreSQL.

---

## 2. Manual DPO Escalation Runbook

When a deletion request is received via support or legal channels:
```bash
# 1. Verify user identity via registered email
# 2. Run soft-deletion management command
python -m scripts.manage_user --delete --email "user@example.com"

# 3. Confirm deletion in audit logs
# 4. Issue formal completion notice to data subject within 30 calendar days
```
