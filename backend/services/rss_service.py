"""MoodFeed Live Turkish News RSS Aggregation Service.

Fetches, parses, and normalizes live RSS feeds from major Turkish news outlets
(BBC Türkçe, DW Türkçe, TRT Haber, NTV, Sputnik Türkiye) into ContentInput models.
"""

from __future__ import annotations

import hashlib
import html
import logging
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any

from backend.ingestion.normalizer import strip_html_tags
from backend.models import ContentInput

logger = logging.getLogger("moodfeed.services.rss")

TURKISH_NEWS_RSS_FEEDS = [
    {
        "name": "BBC Türkçe",
        "url": "https://feeds.bbci.co.uk/turkce/rss.xml",
        "category": "Dünya / Gündem",
    },
    {
        "name": "DW Türkçe",
        "url": "https://rss.dw.com/xml/rss-tur-all",
        "category": "Gündem",
    },
    {
        "name": "TRT Haber",
        "url": "https://www.trthaber.com/gundem_articles.rss",
        "category": "Gündem",
    },
    {
        "name": "NTV Haber",
        "url": "https://www.ntv.com.tr/gundem.rss",
        "category": "Gündem",
    },
    {
        "name": "Sputnik Türkiye",
        "url": "https://sputniknews.com.tr/export/rss2/archive/index.xml",
        "category": "Dünya / Politika",
    },
]


class RSSService:
    """Production RSS Service for live news feed ingestion with caching and error resilience."""

    def __init__(self, cache_ttl_seconds: int = 300, timeout_seconds: int = 5) -> None:
        self.cache_ttl_seconds = cache_ttl_seconds
        self.timeout_seconds = timeout_seconds
        self._cached_items: list[dict[str, Any]] = []
        self._last_fetched: float = 0.0

    def sanitize_text(self, text: str | None) -> str:
        """Sanitizes text by unescaping HTML entities and removing HTML markup."""
        if not text:
            return ""
        unescaped = html.unescape(text.strip())
        return strip_html_tags(unescaped).strip()

    def parse_rss_xml(self, xml_bytes: bytes, source_name: str, default_category: str = "Gündem") -> list[dict[str, Any]]:
        """Parses RSS 2.0 / Atom XML bytes into clean dictionary objects."""
        items: list[dict[str, Any]] = []
        try:
            root = ET.fromstring(xml_bytes)
        except Exception as e:
            logger.debug("XML parse error for %s: %s", source_name, e)
            return items

        # 1. RSS 2.0 (<rss><channel><item> or <channel><item>)
        for item_node in root.findall(".//item"):
            try:
                raw_title = item_node.findtext("title") or "Başlıksız Haber"
                raw_desc = (
                    item_node.findtext("description")
                    or item_node.findtext("{http://purl.org/rss/1.0/modules/content/}encoded")
                    or ""
                )
                link = (item_node.findtext("link") or "").strip()
                pub_date = item_node.findtext("pubDate") or datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M")

                title = self.sanitize_text(raw_title)
                summary = self.sanitize_text(raw_desc)
                if not summary or len(summary) < 5:
                    summary = title

                if not title and not summary:
                    continue

                content_id = f"rss-{hashlib.md5((link or title).encode('utf-8')).hexdigest()[:12]}"

                items.append({
                    "id": content_id,
                    "content_id": content_id,
                    "title": title,
                    "text": summary[:2000],
                    "summary": summary[:2000],
                    "url": link,
                    "link": link,
                    "source": source_name,
                    "author": source_name,
                    "category": default_category,
                    "published_at": pub_date,
                    "time": "Az önce",
                })
            except Exception as item_err:
                logger.debug("Error parsing item in %s: %s", source_name, item_err)
                continue

        # 2. Atom Feed (<feed><entry>)
        atom_ns = "{http://www.w3.org/2005/Atom}"
        for entry_node in root.findall(f".//{atom_ns}entry"):
            try:
                raw_title = entry_node.findtext(f"{atom_ns}title") or "Başlıksız Haber"
                raw_summary = (
                    entry_node.findtext(f"{atom_ns}summary")
                    or entry_node.findtext(f"{atom_ns}content")
                    or ""
                )
                link_el = entry_node.find(f"{atom_ns}link")
                link = link_el.attrib.get("href", "").strip() if link_el is not None else ""
                pub_date = (
                    entry_node.findtext(f"{atom_ns}published")
                    or entry_node.findtext(f"{atom_ns}updated")
                    or datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M")
                )

                title = self.sanitize_text(raw_title)
                summary = self.sanitize_text(raw_summary)
                if not summary:
                    summary = title

                content_id = f"atom-{hashlib.md5((link or title).encode('utf-8')).hexdigest()[:12]}"

                items.append({
                    "id": content_id,
                    "content_id": content_id,
                    "title": title,
                    "text": summary[:2000],
                    "summary": summary[:2000],
                    "url": link,
                    "link": link,
                    "source": source_name,
                    "author": source_name,
                    "category": default_category,
                    "published_at": pub_date,
                    "time": "Az önce",
                })
            except Exception as entry_err:
                logger.debug("Error parsing entry in %s: %s", source_name, entry_err)
                continue

        return items

    def fetch_feed(self, source_info: dict[str, str]) -> list[dict[str, Any]]:
        """Fetches a single remote RSS feed with strict timeout and exception handling."""
        name = source_info.get("name", "Haber Kaynağı")
        url = source_info.get("url", "")
        category = source_info.get("category", "Gündem")

        if not url:
            return []

        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 MoodFeed/1.0",
                    "Accept": "application/rss+xml, application/xml, text/xml, */*",
                },
            )
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                if resp.status == 200:
                    data = resp.read()
                    return self.parse_rss_xml(data, source_name=name, default_category=category)
        except Exception as e:
            logger.warning("[RSS Service] %s feed fetch error (%s): %s", name, url, e)

        return []

    def fetch_all_feeds(self, force_refresh: bool = False) -> list[dict[str, Any]]:
        """Fetches from all configured Turkish RSS feeds, interleaves results, and returns cached data if fresh."""
        now = time.time()
        if not force_refresh and self._cached_items and (now - self._last_fetched < self.cache_ttl_seconds):
            return self._cached_items

        all_feed_results: list[list[dict[str, Any]]] = []
        for src in TURKISH_NEWS_RSS_FEEDS:
            feed_items = self.fetch_feed(src)
            if feed_items:
                all_feed_results.append(feed_items)

        # Interleave items from different sources for a rich and balanced feed
        combined: list[dict[str, Any]] = []
        max_len = max((len(lst) for lst in all_feed_results), default=0)
        for i in range(max_len):
            for feed_list in all_feed_results:
                if i < len(feed_list):
                    combined.append(feed_list[i])

        if combined:
            self._cached_items = combined
            self._last_fetched = now
            logger.info("[RSS Service] Successfully fetched %d live news items from %d sources.", len(combined), len(all_feed_results))
            return combined

        return self._cached_items or []

    def get_live_content_inputs(self, limit: int = 30) -> list[ContentInput]:
        """Converts fetched RSS news items into ContentInput models for reranking pipeline."""
        raw_items = self.fetch_all_feeds()
        if not raw_items:
            return []

        content_inputs: list[ContentInput] = []
        for idx, item in enumerate(raw_items[:limit], start=1):
            try:
                # Calculate initial baseline score
                initial_score = round(0.70 - (idx * 0.005), 3)
                initial_score = max(0.40, min(0.95, initial_score))

                clean_title = (item.get("title") or "").strip()
                clean_summary = (item.get("summary") or item.get("text") or "").strip()
                if clean_title and clean_summary and clean_summary != clean_title:
                    combined_text = f"{clean_title}. {clean_summary}".strip()
                else:
                    combined_text = clean_title or clean_summary or "Haber içeriği"

                cin = ContentInput(
                    id=item.get("id") or f"rss-item-{idx}",
                    text=combined_text[:2000],
                    original_score=initial_score,
                    title=clean_title,
                    url=item.get("url") or item.get("link"),
                    source=item.get("source"),
                    author=item.get("author") or item.get("source"),
                    category=item.get("category") or "Gündem",
                    published_at=item.get("published_at"),
                )
                content_inputs.append(cin)
            except Exception as e:
                logger.debug("Failed to convert RSS item to ContentInput: %s", e)
                continue

        return content_inputs


# Singleton RSS service instance
rss_service = RSSService()
