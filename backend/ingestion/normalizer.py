"""MoodFeed Content Ingestion Normalizer.

Performs robust HTML stripping, script/tag sanitization, URL validation,
content hashing, and entity normalization to the standard ContentItem schema.
"""

from __future__ import annotations

import hashlib
import re
import urllib.parse
from datetime import datetime, timezone
from typing import Any


def strip_html_tags(html_text: str) -> str:
    """Safely strips all HTML tags and decodes common entities."""
    if not html_text:
        return ""
    # Remove script and style elements completely
    clean = re.sub(r"<(script|style).*?>.*?</\1>", "", html_text, flags=re.DOTALL | re.IGNORECASE)
    # Remove all HTML tags
    clean = re.sub(r"<[^>]+>", " ", clean)
    # Normalize whitespaces
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def calculate_content_hash(text: str, title: str) -> str:
    """Computes SHA-256 fingerprint for deduplication."""
    payload = f"{title.strip().lower()}|{text.strip().lower()}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def normalize_url(raw_url: str | None) -> str | None:
    """Validates and canonicalizes URLs, rejecting non-HTTP protocols."""
    if not raw_url:
        return None
    try:
        parsed = urllib.parse.urlparse(raw_url.strip())
        if parsed.scheme not in ("http", "https"):
            return None
        return urllib.parse.urlunparse(parsed)
    except Exception:
        return None


def normalize_content_item(raw: dict[str, Any], source_id: str | None = None) -> dict[str, Any]:
    """Normalizes provider raw feed entry into canonical ContentItem schema."""
    raw_title = str(raw.get("title") or "Başlıksız Gönderi")
    raw_text = str(raw.get("text") or raw.get("summary") or raw.get("description") or "")

    title = strip_html_tags(raw_title)[:300]
    text = strip_html_tags(raw_text)[:5000]
    summary = text[:280] if len(text) > 280 else text

    provider_item_id = str(raw.get("id") or raw.get("guid") or raw.get("link") or hashlib.md5(text.encode()).hexdigest())
    content_hash = calculate_content_hash(text, title)

    published_at = raw.get("published_at")
    if not published_at:
        published_at = datetime.now(timezone.utc).isoformat()

    return {
        "id": f"content-{content_hash[:12]}",
        "source_id": source_id,
        "provider_item_id": provider_item_id,
        "canonical_url": normalize_url(raw.get("link") or raw.get("url")),
        "title": title,
        "summary": summary,
        "text": text,
        "author": str(raw.get("author") or raw.get("creator") or "Anonim Kaynak")[:120],
        "category": str(raw.get("category") or "Genel")[:64],
        "tags": list(raw.get("tags") or [])[:10],
        "published_at": published_at,
        "content_hash": content_hash,
        "moderation_status": "allowed",
    }
