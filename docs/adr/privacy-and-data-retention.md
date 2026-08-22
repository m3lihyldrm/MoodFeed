# Architecture Decision Record: Privacy, Data Rights & Retention Governance

- **Status:** Accepted / Implemented
- **Date:** 2026-08-22
- **Context:** GDPR & KVKK compliance baseline for user control and data minimization.

---

## Decision

1. **Data Minimization:** No raw private content, facial biometrics, camera/microphone streams, or third-party ad tracking scripts are ever stored or processed.
2. **User Data Rights:**
   - Right of Portability: `POST /v1/privacy/data/export` provides structured JSON downloads of personal preferences, bookmarks, and feedback.
   - Right to Erasure: `POST /v1/privacy/data/deletion` immediately terminates active sessions and soft-deletes the user identity, triggering hard deletion after 30 days.
3. **Formula Injection Defense:** CSV exports escape `=, +, -, @` characters with single quotes (`'`).
4. **Consent Management:** Granular consent states for cookies, algorithmic sorting, and research participation.

---

## Consequences

- Full user sovereignty over their profile and interaction history.
- Audit trail for compliance without exposing personal data.
