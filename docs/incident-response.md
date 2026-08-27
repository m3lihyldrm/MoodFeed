# MoodFeed Operational Incident Response Policy

- **Objective:** Establishing structured on-call procedures, escalation paths, and post-mortem standards.

---

## 1. Severity Levels & Escalation Targets

| Severity | Impact | Initial Response SLA | Status Update Frequency |
| :--- | :--- | :--- | :--- |
| **SEV-1 (Critical)** | Complete service outage or active security vulnerability | < 15 minutes | Every 30 minutes |
| **SEV-2 (Major)** | Feed generation failure for subset of users or ML latency spike (> 5s) | < 1 hour | Every 2 hours |
| **SEV-3 (Minor)** | Minor UI cosmetic glitch or export generation queue delay | < 24 hours | Daily |

---

## 2. Post-Mortem Standard

- Any SEV-1 or SEV-2 incident requires a blameless post-mortem document completed within 48 hours covering:
  1. Incident Summary & Timeline
  2. Root Cause Analysis (5 Whys)
  3. Corrective Actions & Preventative Engineering Tasks
