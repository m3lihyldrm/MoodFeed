# Architecture Decision Record: Authentication & Session Management

- **Status:** Accepted / Implemented
- **Date:** 2026-08-22
- **Context:** Production auth and session security baseline for MoodFeed.

---

## Decision

1. **Password Hashing:** PBKDF2-SHA256 with 600,000 iterations and per-user cryptographically random 16-byte salts. Constant-time verification is enforced to prevent timing attacks. Extension point to Argon2id is specified for dedicated hardware environments.
2. **Session Architecture:** Dual-token model with HMAC-SHA256 JWT Access Token (30-minute TTL) and Refresh Token Family (14-day TTL) stored in database with automatic reuse detection and full family revocation upon breach attempt.
3. **Brute Force Defense:** Progressive account lockout enforcing a 15-minute freeze upon 5 consecutive failed login attempts on a single account.
4. **Session Cookies:** `HttpOnly`, `SameSite=Lax` (or `Strict`), and `Secure` attributes required in production.

---

## Consequences

- Zero plain text passwords in memory, logs, or storage.
- High resilience against credential stuffing and brute-force attacks.
- Graceful session refresh without logging out active users.
