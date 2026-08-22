# MoodFeed Consent & Legal Basis Matrix

- **Framework:** GDPR Article 6 & 7 / KVKK Madde 5 & 6

---

## 1. Granular Consent Matrix

| Consent Identifier | Name & Scope | Mandatory / Optional | Default State | Withdrawal Impact |
| :--- | :--- | :--- | :--- | :--- |
| `essential_cookies` | Session authentication and CSRF token cookies | Mandatory for Web App | Granted on Login | Account logout |
| `algorithmic_feed_sorting` | Computing content features and sorting feed items | Mandatory for MoodFeed mode | Opt-in | Feed falls back to Original chronologic order |
| `exploratory_pilot_evaluation` | Participation in task tracking, survey, and research exports | Optional | Opt-in (Explicit modal) | Pilot widgets hidden, research session ended |
| `anonymous_telemetry` | Aggregated error counts and latency metrics (zero PII) | Optional | Opt-out | No performance logs associated with session |

---

## 2. Consent Withdrawal Mechanism

- Users can withdraw consent at any time via `POST /v1/privacy/consents/revoke` or directly inside the **Settings & Privacy** screen in the frontend.
- Withdrawal takes effect immediately without retroactive penalty.
