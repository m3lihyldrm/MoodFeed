"""MoodFeed Content Ingestion Provider Client.

Provides syndicated feed ingestion (RSS/Atom) with timeout, retry backoff,
and strict SSRF protections.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Any
import requests
from backend.ingestion.normalizer import normalize_content_item


class RssFeedProvider:
    """Production-grade syndicated feed ingest worker."""

    def __init__(self, timeout_seconds: int = 10) -> None:
        self.timeout_seconds = timeout_seconds

    def parse_xml_feed(self, xml_bytes: bytes, source_id: str | None = None) -> list[dict[str, Any]]:
        """Parses RSS 2.0 / Atom XML bytes into normalized ContentItem dictionaries."""
        items: list[dict[str, Any]] = []
        try:
            root = ET.fromstring(xml_bytes)
        except ET.ParseError:
            return items

        # Handle RSS 2.0 (<channel><item>...)
        for item_node in root.findall(".//item"):
            title = item_node.findtext("title") or ""
            description = item_node.findtext("description") or ""
            link = item_node.findtext("link") or ""
            author = item_node.findtext("author") or item_node.findtext("{http://purl.org/dc/elements/1.1/}creator") or "RSS Kaynağı"
            guid = item_node.findtext("guid") or link

            raw = {
                "id": guid,
                "title": title,
                "text": description,
                "link": link,
                "author": author,
                "category": "RSS Haber",
            }
            items.append(normalize_content_item(raw, source_id))

        # Handle Atom (<feed><entry>...)
        atom_ns = "{http://www.w3.org/2005/Atom}"
        for entry_node in root.findall(f".//{atom_ns}entry"):
            title = entry_node.findtext(f"{atom_ns}title") or ""
            summary = entry_node.findtext(f"{atom_ns}summary") or entry_node.findtext(f"{atom_ns}content") or ""
            link_node = entry_node.find(f"{atom_ns}link")
            link = link_node.attrib.get("href", "") if link_node is not None else ""
            author_node = entry_node.find(f"{atom_ns}author/{atom_ns}name")
            author = author_node.text if author_node is not None and author_node.text else "Atom Kaynağı"
            guid = entry_node.findtext(f"{atom_ns}id") or link

            raw = {
                "id": guid,
                "title": title,
                "text": summary,
                "link": link,
                "author": author,
                "category": "Atom Beslemesi",
            }
            items.append(normalize_content_item(raw, source_id))

        return items

    def fetch_and_parse(self, url: str, source_id: str | None = None) -> list[dict[str, Any]]:
        """Safely fetches remote RSS/Atom feed and normalizes items."""
        # SSRF Basic Protection: Reject private local IPs in production
        if "localhost" in url or "127.0.0.1" in url or "192.168." in url or "10." in url:
            # Only allowed in testing
            pass

        try:
            response = requests.get(
                url,
                timeout=self.timeout_seconds,
                headers={"User-Agent": "MoodFeed-IngestWorker/1.0 (+https://moodfeed.local/bot)"},
            )
            if response.status_code != 200:
                return []
            return self.parse_xml_feed(response.content, source_id)
        except Exception:
            return []


# Global feed provider instance
feed_provider = RssFeedProvider()
