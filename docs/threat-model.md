# MoodFeed Threat Model & Security Architecture

- **Methodology:** STRIDE (Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege)
- **Standard:** OWASP ASVS v4.0.3 Level 2

---

## 1. Threat Analysis & Mitigations

| STRIDE Category | Threat Description | Attack Vector | Technical Mitigation |
| :--- | :--- | :--- | :--- |
| **Spoofing** | Impersonating another user | Forging JWT token or session hijacking | HMAC-SHA256 signing, cryptographically random secret validation, constant-time verification |
| **Tampering** | Modifying ranking parameters or injecting malicious payloads | Formula injection in CSV exports, SQL injection in queries, XSS in notes | Single-quote escaping in CSV, Pydantic input schemas, `strip_html_tags` on note fields, parameterized queries |
| **Repudiation** | Denying critical account actions or consent changes | User claims they did not delete account or consent | Immutable `audit_events` and `consent_events` tables recording timestamp and hashed IP |
| **Information Disclosure** | Unauthorized cross-tenant data access | IDOR on saved items or user preferences | Repository-level `user_id` filtering, zero token leakage in logs |
| **Denial of Service** | Resource exhaustion or brute-force login | Flooding `/v1/auth/login` or heavy re-ranking queries | Progressive lockout (5 failures = 15 min lock), 10s request timeouts, pagination limits (max 50) |
| **Elevation of Privilege** | Normal user calling admin moderation endpoints | Direct endpoint probing | Role-based access control checking `user["role"] in ("admin", "moderator")` |
