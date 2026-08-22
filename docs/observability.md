# MoodFeed Production Observability & Monitoring Guide

- **Architecture:** OpenTelemetry tracing, Prometheus metrics scraping, and privacy-safe structured JSON logging.

---

## 1. Structured JSON Log Schema

All backend log entries are emitted in single-line JSON format:
```json
{
  "timestamp": "2026-08-22T03:30:00.123Z",
  "level": "INFO",
  "service": "moodfeed-backend",
  "environment": "production",
  "request_id": "req-1724300000",
  "user_id": "u-4a7b9c",
  "route": "/v1/feed",
  "status_code": 200,
  "latency_ms": 2.4,
  "scorer_mode": "rule_based"
}
```

### Strict Log Redaction Rules:
- **Never Logged:** Passwords, JWT secrets, session tokens, raw post text, PII, open feedback text.

---

## 2. Health & Probe Endpoints

- **Liveness Probe:** `GET /v1/system/liveness` -> `{"status": "alive"}` (HTTP 200)
- **Readiness Probe:** `GET /v1/system/readiness` -> Verifies database connectivity and ML model availability.
- **Metrics Endpoint:** `GET /v1/system/metrics` -> Emits Prometheus/JSON runtime metrics.

---

## 3. Production Alerting Rules

| Alert Name | Condition | Severity | Action |
| :--- | :--- | :--- | :--- |
| `High5xxRate` | $>1\%$ HTTP 5xx responses over 5 min | P1 (Critical) | Page On-Call, check error logs |
| `MLScorerFallbackSpike` | Fallback rate $>10\%$ over 10 min | P2 (High) | Inspect transformer memory / CPU load |
| `AuthFailureAnomaly` | $>50$ failed logins in 5 min on single IP | P2 (High) | Verify rate-limiter, enforce IP ban |
| `DatabasePoolExhaustion` | Active pool connections $>90\%$ for 3 min | P1 (Critical) | Scale connection pool, check slow queries |
