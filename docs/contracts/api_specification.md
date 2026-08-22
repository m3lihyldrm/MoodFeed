# MoodFeed Production REST API Specification

**Version:** 1.0.0
**Base URL:** `https://api.moodfeed.app/v1`
**Standard Headers:**
- `Content-Type: application/json`
- `Authorization: Bearer <JWT_ACCESS_TOKEN>` (for authenticated endpoints)
- `X-Request-Id: <UUID>` (for distributed tracing and audit logging)
- `X-Client-Version: <semver>`

---

## 1. Authentication & Identity Endpoints

### `POST /auth/register`
- **Description:** Creates a new user account and registers initial consent.
- **Auth:** Public
- **Rate Limit:** 5 requests / min per IP
- **PII Classification:** CONFIDENTIAL_PII
- **Idempotency:** No
- **Request Body:**
  ```json
  {
    "email": "user@example.com",
    "password": "SecurePassword123!",
    "displayName": "Kullanıcı Adı",
    "initialConsents": ["connected_source_processing", "client_side_ranking"]
  }
  ```
- **Responses:**
  - `201 Created`:
    ```json
    {
      "user": { "id": "u-uuid-001", "email": "user@example.com", "displayName": "Kullanıcı Adı", "role": "user" },
      "accessToken": "jwt.access.token",
      "refreshToken": "jwt.refresh.token",
      "expiresIn": 900
    }
    ```
  - `409 Conflict`: `{"error": {"code": "EMAIL_ALREADY_REGISTERED", "message": "Bu e-posta adresi zaten kayıtlı.", "requestId": "req-001"}}`

---

### `POST /auth/login`
- **Description:** Authenticates user credentials and issues access & refresh tokens.
- **Auth:** Public
- **Rate Limit:** 10 requests / min per IP
- **PII Classification:** CONFIDENTIAL_PII
- **Idempotency:** No
- **Request Body:**
  ```json
  {
    "email": "user@example.com",
    "password": "SecurePassword123!"
  }
  ```
- **Responses:**
  - `200 OK`: Returns User object and JWT tokens.
  - `401 Unauthorized`: `{"error": {"code": "INVALID_CREDENTIALS", "message": "Geçersiz e-posta veya şifre.", "requestId": "req-002"}}`

---

### `POST /auth/logout`
- **Description:** Revokes the current session and invalidates the refresh token family.
- **Auth:** Bearer Token
- **Rate Limit:** 30 requests / min
- **PII Classification:** INTERNAL
- **Idempotency:** Yes
- **Responses:** `200 OK: {"message": "Oturum başarıyla sonlandırıldı."}`

---

### `POST /auth/refresh`
- **Description:** Rotates the refresh token and issues a new access token.
- **Auth:** Public (requires refresh token in body or HttpOnly cookie)
- **Rate Limit:** 20 requests / min
- **PII Classification:** CONFIDENTIAL_PII
- **Idempotency:** No (Token Rotation)

---

### `POST /auth/password-reset`
- **Description:** Triggers a privacy-safe password reset link to user's registered email.
- **Auth:** Public
- **Rate Limit:** 3 requests / hour per email
- **PII Classification:** CONFIDENTIAL_PII
- **Idempotency:** Yes
- **Responses:** `200 OK: {"message": "Eğer hesap mevcutsa sıfırlama bağlantısı gönderildi."}`

---

## 2. User & Consent Endpoints

### `GET /me`
- **Description:** Returns the active user profile, permissions, and account status.
- **Auth:** Bearer Token
- **Rate Limit:** 120 requests / min
- **PII Classification:** CONFIDENTIAL_PII
- **Idempotency:** Yes

---

### `DELETE /me`
- **Description:** Triggers Right-to-Erasure (GDPR Art. 17 / KVKK m. 11). Queues deletion of all user preferences, interactions, saved items, and audit logs.
- **Auth:** Bearer Token (requires password confirmation)
- **Rate Limit:** 2 requests / hour
- **PII Classification:** CONFIDENTIAL_PII
- **Idempotency:** Yes
- **Responses:** `202 Accepted: {"message": "Hesap silme talebi alındı. Tüm veriler 24 saat içinde temizlenecektir."}`

---

### `GET /consents`
- **Description:** Retrieves all active and historical consent records for the user.
- **Auth:** Bearer Token
- **Rate Limit:** 60 requests / min
- **PII Classification:** RESTRICTED

---

### `POST /consents`
- **Description:** Grants or revokes specific privacy consent types.
- **Auth:** Bearer Token
- **Rate Limit:** 30 requests / min
- **PII Classification:** RESTRICTED
- **Idempotency:** Yes
- **Request Body:**
  ```json
  {
    "consentType": "connected_source_processing",
    "status": "granted",
    "version": "2026.1"
  }
  ```

---

## 3. User Preferences Endpoints

### `GET /preferences`
- **Description:** Retrieves the current user ranking sensitivities, profile preset, and muted lists.
- **Auth:** Bearer Token
- **Rate Limit:** 120 requests / min
- **PII Classification:** RESTRICTED

---

### `PATCH /preferences`
- **Description:** Atomically updates one or more user ranking preferences.
- **Auth:** Bearer Token
- **Rate Limit:** 60 requests / min
- **PII Classification:** RESTRICTED
- **Idempotency:** Yes
- **Request Body:**
  ```json
  {
    "profilePreset": "calmer",
    "repetitionSensitivity": "high",
    "negativitySensitivity": "reduce",
    "lowIntensityMode": true
  }
  ```

---

### `POST /preferences/reset`
- **Description:** Restores all ranking preferences to system default (Balanced).
- **Auth:** Bearer Token
- **Rate Limit:** 20 requests / min
- **PII Classification:** RESTRICTED
- **Idempotency:** Yes

---

## 4. Source Management Endpoints

### `GET /sources`
- **Description:** Lists user-connected platforms or synthetic content feeds.
- **Auth:** Bearer Token
- **Rate Limit:** 60 requests / min

---

### `POST /sources/connect`
- **Description:** Initiates OAuth / API token connection to an authorized content source.
- **Auth:** Bearer Token
- **Rate Limit:** 10 requests / min
- **PII Classification:** CONFIDENTIAL_PII

---

### `POST /sources/:id/sync`
- **Description:** Triggers ingestion and feature extraction for a connected source.
- **Auth:** Bearer Token
- **Rate Limit:** 5 requests / min
- **Idempotency:** Yes

---

### `DELETE /sources/:id`
- **Description:** Disconnects a source and immediately purges its ingested content items.
- **Auth:** Bearer Token
- **Rate Limit:** 20 requests / min
- **Idempotency:** Yes

---

## 5. Feed, Ranking & Explanation Endpoints

### `GET /feed`
- **Description:** Returns paginated, scored, and reranked feed items according to user preferences.
- **Auth:** Bearer Token / Public Demo Token
- **Rate Limit:** 180 requests / min
- **PII Classification:** RESTRICTED
- **Query Parameters:**
  - `page`: int (default: 1)
  - `pageSize`: int (default: 10, max: 50)
  - `profile`: "balanced" | "calmer" | "user_control" | "custom"
  - `feedMode`: "moodfeed" | "original"
  - `filter`: "all" | "saved" | "low_density" | "recent"
  - `search`: string (max 80 chars)
  - `scenario`: "default" | "high_negativity"
- **Response `200 OK`:**
  ```json
  {
    "items": [
      {
        "content": {
          "id": "post-001",
          "title": "Ekip Çalışması ve İlerleme",
          "authorName": "Mert Yılmaz",
          "category": "Topluluk",
          "bodyText": "Bugün ekip arkadaşımın desteğiyle...",
          "publishedAt": "2026-08-22T00:10:00Z"
        },
        "feature": {
          "sentimentPolarity": "positive",
          "negativityScore": 0.05,
          "toxicityScore": 0.0,
          "repetitionScore": 0.1
        },
        "originalRank": 1,
        "moodfeedRank": 1,
        "activeRank": 1,
        "rankDelta": 0,
        "rankReason": "Düşük toksisite ve pozitif denge",
        "explanation": {
          "observed": "Pozitif duygu tonu ve çok düşük toksisite sinyali gözlendi.",
          "action": "Akış dengesini korumak için üst sıralardaki konumu pekiştirildi.",
          "control": "İçerik kartından öneriyi geri alabilir veya kaynağı sessize alabilirsiniz.",
          "limitation": "Bu gözlem metin sözlüğüne dayalıdır; klinik duygu durumu tespiti değildir.",
          "mathematicalFormula": "ranking_score = clamp(0.65 - 0.35*0.0 - 0.25*0.05 + 0.15*1.0*0.0) = 0.638",
          "scoreBreakdown": {
            "originalScore": 0.65,
            "toxicityPenalty": 0.0,
            "negativityPenalty": 0.012,
            "diversityBonus": 0.0,
            "finalScore": 0.638
          }
        },
        "isSaved": false,
        "isReverted": false,
        "isMuted": false
      }
    ],
    "totalCount": 10,
    "page": 1,
    "pageSize": 10,
    "hasMore": false,
    "spiralRiskScore": 0.0,
    "spiralRiskLevel": "low",
    "scorerMode": "rule_based",
    "processingTimeMs": 2.45
  }
  ```

---

### `GET /feed/:contentId`
- **Description:** Returns detailed metadata and signal breakdown for a single content item.
- **Auth:** Bearer Token
- **Rate Limit:** 120 requests / min

---

### `GET /feed/:contentId/explanation`
- **Description:** Returns the 4-pillar explainability breakdown for a specific ranking decision.
- **Auth:** Bearer Token
- **Rate Limit:** 120 requests / min

---

### `POST /feed/:contentId/feedback`
- **Description:** Records an explicit user interaction (e.g. undo recommendation, reduce similar content).
- **Auth:** Bearer Token
- **Rate Limit:** 60 requests / min
- **Idempotency:** Yes
- **Request Body:**
  ```json
  {
    "action": "undo_recommendation",
    "reason": "Orijinal sıralamayı tercih ediyorum."
  }
  ```

---

### `POST /feed/:contentId/save` & `DELETE /feed/:contentId/save`
- **Description:** Saves or unsaves a content item in the user's bookmarks list.
- **Auth:** Bearer Token
- **Rate Limit:** 120 requests / min
- **Idempotency:** Yes

---

### `POST /sources/:sourceId/mute` & `DELETE /sources/:sourceId/mute`
- **Description:** Adds or removes a source/author from the user's muted list.
- **Auth:** Bearer Token
- **Rate Limit:** 60 requests / min
- **Idempotency:** Yes

---

### `GET /compare`
- **Description:** Returns side-by-side comparison dataset of Original platform order vs MoodFeed order with delta statistics.
- **Auth:** Bearer Token
- **Rate Limit:** 60 requests / min

---

### `GET /insights`
- **Description:** Returns aggregate category distributions and session exposure metrics calculated from user interactions.
- **Auth:** Bearer Token
- **Rate Limit:** 60 requests / min

---

## 6. Pilot Evaluation & Export Endpoints

### `POST /pilot/sessions`
- **Description:** Initializes an anonymous or user-scoped exploratory pilot evaluation session.
- **Auth:** Bearer Token / Anonymous Session Header
- **Rate Limit:** 10 requests / hour per IP
- **Idempotency:** Yes

---

### `PATCH /pilot/sessions/:id`
- **Description:** Submits completed pilot tasks, durations, error counts, Likert ratings, and open feedback.
- **Auth:** Bearer Token / Session Header
- **Rate Limit:** 30 requests / min

---

### `POST /exports` & `GET /exports/:id`
- **Description:** Initiates and downloads formula-injection-safe JSON / CSV export of user session or account data archive.
- **Auth:** Bearer Token
- **Rate Limit:** 5 requests / hour
- **Idempotency:** Yes

---

### `POST /data/export` & `POST /data/delete`
- **Description:** Full GDPR / KVKK Data Subject Rights (Access & Erasure) asynchronous dispatch endpoints.
- **Auth:** Bearer Token with Re-Authentication
- **Rate Limit:** 2 requests / day
- **Idempotency:** Yes
