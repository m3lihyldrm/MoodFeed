"""MoodFeed RSS Feed Ingestion Module.

Fetches and normalizes syndicated RSS/Atom news feeds, sanitizes HTML,
and prepares structured post records for analysis and persistence.
"""

from __future__ import annotations

import html
import re
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any
import requests

from backend.ingestion.normalizer import strip_html_tags, calculate_content_hash


DEFAULT_RSS_FEED_URL = "https://rss.haberler.com/rss.asp"


class RSSFeedParser:
    """Production RSS & Atom XML Feed Parser with sanitization."""

    def __init__(self, timeout_seconds: int = 10) -> None:
        self.timeout_seconds = timeout_seconds

    def sanitize_text(self, text: str | None) -> str:
        """Sanitizes text by stripping HTML tags and decoding entities."""
        if not text:
            return ""
        unescaped = html.unescape(text)
        return strip_html_tags(unescaped)

    def parse_xml(self, xml_content: str | bytes) -> list[dict[str, Any]]:
        """Parses raw RSS 2.0 or Atom XML content into normalized dictionaries."""
        items: list[dict[str, Any]] = []
        if isinstance(xml_content, str):
            xml_bytes = xml_content.encode("utf-8")
        else:
            xml_bytes = xml_content

        try:
            root = ET.fromstring(xml_bytes)
        except ET.ParseError:
            return items

        # 1. Check for standard RSS 2.0 items (<rss><channel><item>...)
        for item_node in root.findall(".//item"):
            raw_title = item_node.findtext("title") or "Başlıksız Haber"
            raw_desc = item_node.findtext("description") or item_node.findtext("{http://purl.org/rss/1.0/modules/content/}encoded") or ""
            link = item_node.findtext("link") or ""
            author = (
                item_node.findtext("author")
                or item_node.findtext("{http://purl.org/dc/elements/1.1/}creator")
                or "Haber Kaynağı"
            )
            category = item_node.findtext("category") or "Gündem"
            pub_date = item_node.findtext("pubDate") or datetime.now(timezone.utc).isoformat()
            guid = item_node.findtext("guid") or link

            title = self.sanitize_text(raw_title)[:250]
            clean_text = self.sanitize_text(raw_desc)[:4000]
            if not clean_text:
                clean_text = title

            content_hash = calculate_content_hash(clean_text, title)

            items.append({
                "guid": guid,
                "title": title,
                "text": clean_text,
                "link": link,
                "author": self.sanitize_text(author)[:100],
                "category": self.sanitize_text(category)[:60],
                "published_at": pub_date,
                "content_hash": content_hash,
                "source": "rss",
            })

        # 2. Check for Atom entries (<feed><entry>...)
        atom_ns = "{http://www.w3.org/2005/Atom}"
        for entry_node in root.findall(f".//{atom_ns}entry"):
            raw_title = entry_node.findtext(f"{atom_ns}title") or "Başlıksız Haber"
            raw_summary = (
                entry_node.findtext(f"{atom_ns}summary")
                or entry_node.findtext(f"{atom_ns}content")
                or ""
            )
            link_el = entry_node.find(f"{atom_ns}link")
            link = link_el.attrib.get("href", "") if link_el is not None else ""
            author_el = entry_node.find(f"{atom_ns}author/{atom_ns}name")
            author = author_el.text if author_el is not None and author_el.text else "Atom Kaynağı"
            category_el = entry_node.find(f"{atom_ns}category")
            category = category_el.attrib.get("term", "Gündem") if category_el is not None else "Gündem"
            pub_date = (
                entry_node.findtext(f"{atom_ns}published")
                or entry_node.findtext(f"{atom_ns}updated")
                or datetime.now(timezone.utc).isoformat()
            )
            guid = entry_node.findtext(f"{atom_ns}id") or link

            title = self.sanitize_text(raw_title)[:250]
            clean_text = self.sanitize_text(raw_summary)[:4000]
            if not clean_text:
                clean_text = title

            content_hash = calculate_content_hash(clean_text, title)

            items.append({
                "guid": guid,
                "title": title,
                "text": clean_text,
                "link": link,
                "author": self.sanitize_text(author)[:100],
                "category": self.sanitize_text(category)[:60],
                "published_at": pub_date,
                "content_hash": content_hash,
                "source": "atom",
            })

        return items

    def fetch_feed(self, url: str = DEFAULT_RSS_FEED_URL) -> list[dict[str, Any]]:
        """Fetches and parses a remote RSS or Atom feed."""
        try:
            resp = requests.get(
                url,
                timeout=self.timeout_seconds,
                headers={"User-Agent": "MoodFeed-NewsCollector/1.0 (+https://moodfeed.local)"},
            )
            if resp.status_code == 200:
                return self.parse_xml(resp.content)
            return []
        except Exception:
            return []


# Singleton parser
rss_parser = RSSFeedParser()
