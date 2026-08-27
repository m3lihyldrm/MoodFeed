# MoodFeed Production Product Foundation & Architecture

**Target Environment:** Production SaaS / Microservices or Modular Monolith
**Compliance Standards:** OWASP ASVS v4.0.3 Level 2, GDPR Art. 17/20, KVKK m. 11, WCAG 2.2 Level AA
**Status:** Production Readiness Foundation Specification

---

## 1. Executive Summary & Core Product Loop

MoodFeed is an explainable feed reranker and signal visibility platform designed to empower users with transparent control over social media content repetition, intensity, and negativity exposure.

### Core Value Loop
$$\text{Ingest / Demo Feed} \longrightarrow \text{Signal Extraction} \longrightarrow \text{Deterministic Reranking} \longrightarrow \text{4-Pillar Explanation} \longrightarrow \text{User Control (Undo / Mute / Preferences)} \longrightarrow \text{A/B Comparison \& Insights}$$

---

## 2. Backend Implementation Architecture

```
[ Frontend SPA (Vanilla JS / React / Vue) ]
                    │
                    ▼  HTTPS / TLS 1.3
[ API Gateway / Cloudflare Reverse Proxy (WAF, Rate Limiting, DDoS Protection) ]
                    │
                    ▼
[ FastAPI / Python 3.11 Production Application Server (Gunicorn + Uvicorn Workers) ]
   ├── Authentication & Session Module (JWT Rotation + Redis Token Blacklist)
   ├── Consent & Privacy Governance Engine (Audit trail, retention worker)
   ├── Content Ingestion & Normalization Worker (Celery / Redis Queue)
   ├── Scoring & NLP Feature Extraction Engine (Rule-based default + BERTurk ML fallback)
   ├── Deterministic Reranking Service (Vectorized scoring, pagination cursors)
   └── Explainability & Transparency Generator
                    │
      ┌─────────────┴─────────────┐
      ▼                           ▼
[ PostgreSQL 16 ]           [ Redis 7 Cluster ]
(Relational Schema,          (Session cache, Rate limits,
 ACID Transactions)           Idempotency keys)
```

### 2.1 Database Relational Schema (PostgreSQL 16)
```sql
-- 1. Users Table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    role VARCHAR(20) DEFAULT 'user' NOT NULL,
    status VARCHAR(30) DEFAULT 'active' NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- 2. Consents Audit Log
CREATE TABLE user_consents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    consent_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    version VARCHAR(20) NOT NULL,
    granted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    revoked_at TIMESTAMP WITH TIME ZONE
);
CREATE INDEX idx_user_consents_lookup ON user_consents(user_id, consent_type);

-- 3. User Preferences
CREATE TABLE user_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    profile_preset VARCHAR(30) DEFAULT 'balanced' NOT NULL,
    repetition_sensitivity VARCHAR(20) DEFAULT 'medium' NOT NULL,
    negativity_sensitivity VARCHAR(20) DEFAULT 'reduce' NOT NULL,
    intensity_sensitivity VARCHAR(20) DEFAULT 'balanced' NOT NULL,
    diversity_preference VARCHAR(20) DEFAULT 'balanced' NOT NULL,
    grouping_enabled BOOLEAN DEFAULT FALSE NOT NULL,
    low_intensity_mode BOOLEAN DEFAULT FALSE NOT NULL,
    show_explanations VARCHAR(20) DEFAULT 'feed_cards' NOT NULL,
    active_feed_mode VARCHAR(20) DEFAULT 'moodfeed' NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- 4. Content Items
CREATE TABLE content_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id VARCHAR(255),
    source_identifier VARCHAR(100) NOT NULL,
    source_label VARCHAR(100),
    author_name VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    summary TEXT,
    body_text TEXT NOT NULL,
    published_at TIMESTAMP WITH TIME ZONE NOT NULL,
    is_synthetic BOOLEAN DEFAULT FALSE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);
CREATE INDEX idx_content_published ON content_items(published_at DESC);

-- 5. Content Extracted Features
CREATE TABLE content_features (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_id UUID UNIQUE NOT NULL REFERENCES content_items(id) ON DELETE CASCADE,
    sentiment_polarity VARCHAR(20) NOT NULL,
    sentiment_score NUMERIC(5, 4) NOT NULL,
    negativity_score NUMERIC(5, 4) NOT NULL,
    toxicity_score NUMERIC(5, 4) NOT NULL,
    repetition_score NUMERIC(5, 4) NOT NULL,
    intensity_score NUMERIC(5, 4) NOT NULL,
    model_engine VARCHAR(30) NOT NULL,
    extracted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- 6. Recommendation Feedback & Undo Log
CREATE TABLE recommendation_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content_id UUID NOT NULL REFERENCES content_items(id) ON DELETE CASCADE,
    action VARCHAR(50) NOT NULL,
    original_rank INT NOT NULL,
    proposed_rank INT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);
```

---

## 3. Mathematical Ranking Architecture

### 3.1 Ranking Formula Specification
For any content $c \in \mathcal{C}$ and user profile $p \in \mathcal{P}$:

$$\text{ranking\_score}(c) = \text{clamp}_{[0.0, 1.0]}\left( S_{\text{orig}}(c) - W_{\text{tox}}(p) \cdot T(c) - W_{\text{neg}}(p) \cdot N(c) \cdot R + W_{\text{div}}(p) \cdot D(c) \cdot R \right)$$

Where:
- $S_{\text{orig}}(c) \in [0.0, 1.0]$: Base platform chronological/engagement score.
- $T(c) \in [0.0, 1.0]$: Hybrid toxicity detection signal.
- $N(c) \in [0.0, 1.0]$: Negative polarity penalty signal.
- $D(c) \in [0.0, 1.0]$: Constructive diversity & topic freshness bonus.
- $R \in [0.0, 1.0]$: Active rolling negative spiral risk coefficient.
- $W_{\text{tox}}, W_{\text{neg}}, W_{\text{div}}$: Sensitivity weight profiles.

### 3.2 Weight Presets
| Profile Preset | $W_{\text{tox}}$ (Toxicity) | $W_{\text{neg}}$ (Negativity) | $W_{\text{div}}$ (Diversity) | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **Balanced (Default)** | $0.35$ | $0.25$ | $0.15$ | Standard balanced feed |
| **Calmer** | $0.50$ | $0.40$ | $0.25$ | High sensitivity to hostility and repetitive stress |
| **User Control** | $0.15$ | $0.10$ | $0.05$ | Minimal algorithmic intervention |

### 3.3 Properties of the Decision Engine
1. **Determinism:** Given identical content features and preference state, outputs are 100% reproducible with stable ordering.
2. **Stable Pagination:** Cursor-based pagination using `(ranking_score, content_id)` compound index prevents item jumping during real-time updates.
3. **Zero Content Deletion:** Contents are never deleted or hidden by the algorithm; ranking simply adjusts relative presentation priority.
4. **Fallback Safety:** If experimental neural models fail, the system falls back seamlessly to rule-based lexical scoring with zero 500 errors.

---

## 4. Privacy & Data Governance (GDPR / KVKK)

1. **Consent Gating:** Processing of connected sources requires explicit opt-in via `POST /consents`.
2. **Zero Storage Demo Mode:** When operating in Demo/Pilot mode, all state resides in volatile JavaScript RAM; zero cookies, localStorage, or tracking pixels are utilized.
3. **Data Minimization:** No biometric mood estimation, camera analysis, keystroke tracking, or personal chat ingestion is performed.
4. **Right to Erasure (RTBF):** `DELETE /me` and `POST /data/delete` trigger automated cryptographic shredding of user records and associated feature vectors within 24 hours.
5. **Privacy-Safe Audit Logs:** IP addresses are hashed using salted SHA-256; raw content bodies are excluded from application telemetry and error tracking logs.

---

## 5. Security Architecture (OWASP ASVS Matrix)

| Category | Control Description | Implementation Detail |
| :--- | :--- | :--- |
| **Authentication** | Password Hashing | Argon2id with salt length 16 bytes, memory cost 64MB |
| **Session Security** | JWT Rotation | Short-lived Access Token (15 min) + Refresh Token Rotation in Redis |
| **XSS Prevention** | Strict Output Encoding | Automatic DOM text node binding, zero `eval` or unsafe `innerHTML` |
| **CSRF Defense** | Anti-CSRF Protection | SameSite=Strict cookies + Double-submit CSRF tokens on mutating requests |
| **SQL Injection** | Parameterized Queries | SQLAlchemy ORM / Parameterized Asyncpg queries |
| **Formula Injection** | CSV Export Sanitization | Prepends single quote `'` to cells starting with `=`, `+`, `-`, `@`, `\t` |
| **Security Headers** | HTTP Security Headers | `Content-Security-Policy: default-src 'self'`, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Strict-Transport-Security: max-age=63072000` |
| **Rate Limiting** | Tiered Token Bucket | Redis-backed token bucket per IP and per authenticated user ID |

---

## 6. Observability & Monitoring

### 6.1 Structured JSON Log Standard
```json
{
  "timestamp": "2026-08-22T03:15:00.123Z",
  "level": "INFO",
  "service": "moodfeed-api",
  "request_id": "req-8f92a1c0",
  "endpoint": "/v1/feed",
  "method": "GET",
  "status_code": 200,
  "duration_ms": 3.12,
  "user_id_hash": "a94f8fe5ccb19ba6",
  "scorer_mode": "rule_based",
  "items_ranked": 10
}
```

### 6.2 Key Operational Metrics (Prometheus)
- `moodfeed_http_requests_total{endpoint, status_code}`
- `moodfeed_ranking_duration_seconds{profile}` (P95 < 15ms)
- `moodfeed_scorer_fallback_total{reason}`
- `moodfeed_user_undo_events_total{profile}`
- `moodfeed_active_sessions_gauge`

---

## 7. Operations & Deployment Runbooks

### 7.1 CI/CD Pipeline Stages
1. **Lint & Static Analysis:** `ruff check backend`, `mypy backend`, `eslint frontend`
2. **Automated Testing:** `pytest --cov=backend tests/` (100% pass threshold)
3. **Security Audit:** `bandit -r backend`, `trivy image scan`
4. **Container Build:** Multi-stage Docker build targeting distroless base image
5. **Staging Deploy & Smoke Test:** Automated health & `/health` verification
6. **Blue/Green Production Rollout:** Zero-downtime traffic switch with automated rollback on error rate $>0.5\%$

### 7.2 Health & Readiness Probes
- `GET /health/live`: Returns `200 OK` if the Python process is responding.
- `GET /health/ready`: Returns `200 OK` only if PostgreSQL and Redis connections are established.

### 7.3 Incident Recovery Runbook
- **Scorer Degradation Incident:** If BERTurk model latency exceeds 50ms or inference errors occur, the circuit breaker automatically switches traffic to `rule_based_fallback` mode without operator intervention.
- **Rollback Command:** `docker service rollback moodfeed_app` or Kubernetes `kubectl rollout undo deployment/moodfeed-api`.
