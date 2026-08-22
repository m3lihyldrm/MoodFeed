# MoodFeed Data Subject Rights & Request Procedures

- **Applicable Frameworks:** GDPR (Articles 15-22) / KVKK (Madde 11)
- **Status:** Baseline Specification (Requires Legal Team Review)

---

## 1. Supported Rights

1. **Right of Access (GDPR Art. 15 / KVKK m. 11/a-c):**
   - Users can review their active session list, current preferences, and connected sources via `/v1/preferences` and `/v1/auth/me`.
2. **Right to Rectification (GDPR Art. 16 / KVKK m. 11/d):**
   - Users can update their display name, profile preset, and filter preferences at any time.
3. **Right to Erasure (GDPR Art. 17 / KVKK m. 11/e):**
   - Self-service deletion via `POST /v1/privacy/data/deletion`. Immediately revokes tokens and schedules permanent database scrubbing.
4. **Right to Data Portability (GDPR Art. 20 / KVKK m. 11/f):**
   - Structured machine-readable export via `POST /v1/privacy/data/export` (JSON / CSV format).
5. **Right to Object / Opt-Out (GDPR Art. 21 / KVKK m. 11/g):**
   - One-click toggle back to Original Feed mode, bypassing all algorithmic re-ranking.

---

## 2. Operational SLAs

- **Self-Service Requests:** Instant (< 2 seconds).
- **Manual Inquiries / Legal Escalations:** Response within 30 calendar days via designated Data Protection Officer.
