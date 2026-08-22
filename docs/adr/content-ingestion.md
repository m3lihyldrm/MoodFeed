# Architecture Decision Record: Content Ingestion & Normalization

- **Status:** Accepted / Implemented
- **Date:** 2026-08-22
- **Context:** Safely ingesting content from syndication feeds without privacy leaks or XSS vulnerabilities.

---

## Decision

1. **Permitted Sources:** Closed beta content ingestion is limited to syndicated RSS 2.0 and Atom XML feeds with explicit user connection. Direct messaging scraping or unauthorized social media scraping is strictly prohibited.
2. **Sanitization:** All raw HTML tags and script elements are stripped via `strip_html_tags` regex sanitizer before feature extraction.
3. **Deduplication:** Content items are hashed using SHA-256 (`calculate_content_hash`) over normalized title and body text. Canonical URLs are validated against safe schemes (`http`, `https`).
4. **Resilience:** HTTP timeouts (10s), exponential backoff, and size limits (max 500KB per XML document) prevent SSRF and DoS vectors.

---

## Consequences

- Clean, script-free text inputs for scoring and ranking engines.
- Zero private user content ingested or stored.
- Resilient ingestion worker with predictable resource utilization.
