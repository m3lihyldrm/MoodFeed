# MoodFeed Privacy Data Map & Governance Framework

- **Standard:** GDPR (EU 2016/679) & KVKK (6698 Sayılı Kanun) Compliance Baseline
- **Version:** 1.0.0
- **Last Updated:** 2026-08-22

---

## 1. Data Classification Matrix

| Data Element | Classification | Legal Basis | Storage Location | Retention Period | Access Controls | User Control |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **User Identity (`email`, `password_hash`, `display_name`)** | Confidential / Personal (PII) | Contractual Necessity (GDPR Art. 6(1)(b)) | PostgreSQL `users` table | Until account deletion + 30 days grace | Admin / Self (RLS) | Full update / Delete |
| **Active Sessions (`session_token`, `ip_address`, `user_agent`)** | Internal / Technical | Legitimate Interest (Security - GDPR Art. 6(1)(f)) | PostgreSQL `sessions` | 14 days or until logout | System Auth Service | Revoke all sessions |
| **Consent Records (`consent_type`, `granted`, `ip_hash`)** | Compliance Audit | Legal Obligation (GDPR Art. 7(1)) | PostgreSQL `consents` | 2 years (Statute of limitations) | Data Protection Officer / System | View / Revoke optional |
| **User Preferences (`profile_preset`, `low_intensity_mode`, `active_feed_mode`)** | User Config | Consent (GDPR Art. 6(1)(a)) | PostgreSQL `user_preferences` | Until updated or reset | Self (RLS) | Instant reset & edit |
| **Content Features (`sentiment`, `toxicity_score`, `repetition_score`)** | Algorithmic Metadata | Legitimate Interest (Feed Sorting) | PostgreSQL `content_features` | 90 days rolling | Read-only Ranking Engine | N/A (Public/Normalized text) |
| **Saved Items (`user_id`, `content_id`)** | User Bookmark | User Initiated | PostgreSQL `saved_items` | Until removed by user | Self (RLS) | Instant deletion |
| **Muted Sources / Categories** | User Filter Rule | User Initiated | PostgreSQL `muted_sources` | Until unmuted by user | Self (RLS) | Instant toggle |
| **Recommendation Feedback** | User Interaction | Consent (Algorithmic Improvement) | PostgreSQL `recommendation_feedback` | 90 days rolling | Anonymized Analytics | Delete with account |
| **Pilot Evaluation Sessions** | Pseudonymous Research | Explicit Separate Consent | PostgreSQL `pilot_sessions` | 60 days after study conclusion | Research Team (No PII) | RAM reset / Export |

---

## 2. Sensitive Data Invariants

1. **Zero Raw Private Content Copying:** Private messages, camera/microphone streams, or biometric feeds are never ingested or analyzed.
2. **No Health / Mental State Claims:** Text analysis operates exclusively on descriptive linguistic features (e.g., negative keyword density); clinical mood or diagnostic labeling is strictly prohibited.
3. **No Third-Party Analytics / Trackers:** External advertising scripts, behavioral tracking beacons, or cross-site fingerprinting are strictly blocked.
