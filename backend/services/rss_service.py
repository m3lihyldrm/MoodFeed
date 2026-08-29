"""MoodFeed Live Turkish News RSS Aggregation & Persistent Archive Service.

Fetches, normalizes, deduplicates, and persists news feeds from 40+ Turkish sources
across 10 core categories (Gündem, Dünya, Ekonomi, Teknoloji, Bilim, Kültür/Sanat, Spor, Sağlık, Çevre/İklim, Eğitim).
Features:
- Never deletes existing valid records on ingestion (incremental archiving).
- Multi-tier deduplication (original_url -> normalized_title+source -> content_hash).
- 6-class Mood AI classification (calm, happy, neutral, anxious, sad, angry).
- Ingestion job locking to prevent concurrent runs.
- Automated data retention cleanup (default 90 days).
- Comprehensive structured logging and real-time metrics.
- Resilient HTTP fetching via httpx with modern User-Agent, redirects, retries, and encoding fallback.
"""

from __future__ import annotations

import asyncio
import datetime
import email.utils
import hashlib
import html
import logging
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any
import uuid

import httpx

try:
    from backend.ingestion.normalizer import (
        calculate_content_hash,
        normalize_title,
        normalize_turkish_lower,
        strip_html_tags,
    )
    from backend.models import ContentInput
    from backend.services.mood_detector import mood_detector
    from backend.config import settings
except ImportError:
    from ingestion.normalizer import (
        calculate_content_hash,
        normalize_title,
        normalize_turkish_lower,
        strip_html_tags,
    )
    from models import ContentInput
    from services.mood_detector import mood_detector
    from config import settings

logger = logging.getLogger("moodfeed.services.rss")

# ==============================================================================
# 1. VERIFIED TURKISH NEWS RSS FEEDS (40+ Sources across 10 Categories)
# ==============================================================================

TURKISH_NEWS_RSS_FEEDS = [
    # 1. GÜNDEM / GENEL
    {"name": "TRT Gündem", "url": "https://www.trthaber.com/gundem_articles.rss", "category": "Gündem"},
    {"name": "TRT Manşet", "url": "https://www.trthaber.com/manset_articles.rss", "category": "Gündem"},
    {"name": "TRT Son Dakika", "url": "https://www.trthaber.com/sondakika_articles.rss", "category": "Gündem"},
    {"name": "NTV Gündem", "url": "https://www.ntv.com.tr/gundem.rss", "category": "Gündem"},
    {"name": "NTV Türkiye", "url": "https://www.ntv.com.tr/turkiye.rss", "category": "Gündem"},
    {"name": "HaberTürk RSS", "url": "https://www.haberturk.com/rss", "category": "Gündem"},
    {"name": "HaberTürk Manşet", "url": "https://www.haberturk.com/rss/manset.xml", "category": "Gündem"},
    {"name": "HaberTürk Gündem", "url": "https://www.haberturk.com/rss/kategori/gundem.xml", "category": "Gündem"},
    {"name": "Sözcü Gündem", "url": "https://www.sozcu.com.tr/feeds-haberler", "category": "Gündem"},
    {"name": "Milliyet Gündem", "url": "https://www.milliyet.com.tr/rss/rssnew/gundemrss.xml", "category": "Gündem"},
    {"name": "Hürriyet Gündem", "url": "https://www.hurriyet.com.tr/rss/gundem", "category": "Gündem"},
    {"name": "Cumhuriyet Son Dakika", "url": "https://www.cumhuriyet.com.tr/rss/son_dakika.xml", "category": "Gündem"},
    {"name": "Ensonhaber Gündem", "url": "https://www.ensonhaber.com/rss/gundem.xml", "category": "Gündem"},

    # 2. DÜNYA - TÜRKÇE
    {"name": "BBC Türkçe", "url": "https://www.bbc.com/turkce/index.xml", "category": "Dünya"},
    {"name": "BBC Türkçe RSS", "url": "https://feeds.bbci.co.uk/turkce/rss.xml", "category": "Dünya"},
    {"name": "DW Türkçe", "url": "https://www.dw.com/tr/rss", "category": "Dünya"},
    {"name": "DW Türkçe All", "url": "https://rss.dw.com/xml/rss-tur-all", "category": "Dünya"},
    {"name": "Euronews Türkçe", "url": "https://tr.euronews.com/rss", "category": "Dünya"},
    {"name": "NTV Dünya", "url": "https://www.ntv.com.tr/dunya.rss", "category": "Dünya"},
    {"name": "Hürriyet Dünya", "url": "https://www.hurriyet.com.tr/rss/dunya", "category": "Dünya"},
    {"name": "TRT Dünya", "url": "https://www.trthaber.com/dunya_articles.rss", "category": "Dünya"},

    # 3. EKONOMİ & FİNANS
    {"name": "TRT Ekonomi", "url": "https://www.trthaber.com/ekonomi_articles.rss", "category": "Ekonomi"},
    {"name": "NTV Ekonomi", "url": "https://www.ntv.com.tr/ekonomi.rss", "category": "Ekonomi"},
    {"name": "HaberTürk Ekonomi", "url": "https://www.haberturk.com/rss/kategori/ekonomi.xml", "category": "Ekonomi"},
    {"name": "Hürriyet Ekonomi", "url": "https://www.hurriyet.com.tr/rss/ekonomi", "category": "Ekonomi"},
    {"name": "Cumhuriyet Ekonomi", "url": "https://www.cumhuriyet.com.tr/rss/ekonomi.xml", "category": "Ekonomi"},
    {"name": "BloombergHT", "url": "https://www.bloomberght.com/rss", "category": "Ekonomi"},
    {"name": "Dünya Gazetesi", "url": "https://www.dunya.com/rss", "category": "Ekonomi"},

    # 4. TEKNOLOJİ & BİLİM
    {"name": "Webtekno XML", "url": "https://www.webtekno.com/rss.xml", "category": "Teknoloji"},
    {"name": "ShiftDelete.Net", "url": "https://www.shiftdelete.net/feed/", "category": "Teknoloji"},
    {"name": "DonanımHaber Tüm", "url": "https://www.donanimhaber.com/rss/tum/", "category": "Teknoloji"},
    {"name": "TRT Bilim Teknoloji", "url": "https://www.trthaber.com/bilim_teknoloji_articles.rss", "category": "Teknoloji"},
    {"name": "NTV Teknoloji", "url": "https://www.ntv.com.tr/teknoloji.rss", "category": "Teknoloji"},
    {"name": "HaberTürk Teknoloji", "url": "https://www.haberturk.com/rss/kategori/teknoloji.xml", "category": "Teknoloji"},
    {"name": "Hürriyet Teknoloji", "url": "https://www.hurriyet.com.tr/rss/teknoloji", "category": "Teknoloji"},
    {"name": "Webrazzi", "url": "https://webrazzi.com/feed/", "category": "Teknoloji"},
    {"name": "Chip Online", "url": "https://www.chip.com.tr/rss/", "category": "Teknoloji"},
    {"name": "Evrim Ağacı", "url": "https://evrimagaci.org/rss.xml", "category": "Bilim"},
    {"name": "Arkeofili", "url": "https://arkeofili.com/feed/", "category": "Bilim"},

    # 5. KÜLTÜR, SPOR, SAĞLIK, ÇEVRE, EĞİTİM
    {"name": "TRT Kültür Sanat", "url": "https://www.trthaber.com/kultur_sanat_articles.rss", "category": "Kültür"},
    {"name": "TRT Spor", "url": "https://www.trthaber.com/spor_articles.rss", "category": "Spor"},
    {"name": "NTV Spor", "url": "https://www.ntv.com.tr/sporskor.rss", "category": "Spor"},
    {"name": "HaberTürk Spor", "url": "https://www.haberturk.com/rss/kategori/spor.xml", "category": "Spor"},
    {"name": "Hürriyet Spor", "url": "https://www.hurriyet.com.tr/rss/spor", "category": "Spor"},
    {"name": "Fotomaç", "url": "https://www.fotomac.com.tr/rss/anasayfa.xml", "category": "Spor"},
    {"name": "TRT Sağlık", "url": "https://www.trthaber.com/saglik_articles.rss", "category": "Sağlık"},
    {"name": "NTV Sağlık", "url": "https://www.ntv.com.tr/saglik.rss", "category": "Sağlık"},
    {"name": "Yeşil Gazete", "url": "https://yesilgazete.org/feed/", "category": "Çevre"},
    {"name": "İklim Haber", "url": "https://www.iklimhaber.org/feed/", "category": "Çevre"},
    {"name": "TRT Eğitim", "url": "https://www.trthaber.com/egitim_articles.rss", "category": "Eğitim"},
    {"name": "Hürriyet Eğitim", "url": "https://www.hurriyet.com.tr/rss/egitim", "category": "Eğitim"},
]

# Backward-compatibility flat URL list
RSS_FEEDS = [src["url"] for src in TURKISH_NEWS_RSS_FEEDS]

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 MoodFeed/1.0"
)
ACCEPT_HEADER = "application/rss+xml, application/xml, text/xml, application/atom+xml, text/html, */*"


class RSSService:
    """Production RSS Service for live news feed ingestion, deduplication, and persistent archiving."""

    def __init__(self, cache_ttl_seconds: int = 45, timeout_seconds: int = 8) -> None:
        self.cache_ttl_seconds = cache_ttl_seconds
        self.timeout_seconds = timeout_seconds
        self._cached_items: list[dict[str, Any]] = []
        self._last_fetched: float = 0.0
        self._last_ingested_at: datetime.datetime | None = None
        self._is_ingesting: bool = False
        self._ingestion_thread_lock = threading.Lock()
        self._async_lock: asyncio.Lock | None = None
        self._last_error: str | None = None
        self._last_summary: dict[str, Any] = {
            "configured_feed_count": len(TURKISH_NEWS_RSS_FEEDS),
            "feeds_checked": 0,
            "feeds_succeeded": 0,
            "feeds_failed": 0,
            "failed_feeds": 0,
            "items_fetched": 0,
            "fetched_items": 0,
            "items_normalized": 0,
            "items_inserted": 0,
            "inserted": 0,
            "items_updated": 0,
            "updated": 0,
            "duplicates_skipped": 0,
            "storage_mode": "uninitialized",
            "elapsed_seconds": 0.0,
            "duration_seconds": 0.0,
            "errors_summary": None,
        }

    @property
    def last_summary(self) -> dict[str, Any]:
        return dict(self._last_summary)

    @property
    def last_error(self) -> str | None:
        return self._last_error

    @property
    def is_ingesting(self) -> bool:
        return self._is_ingesting

    @property
    def last_ingested_at_iso(self) -> str:
        if self._last_ingested_at:
            return self._last_ingested_at.isoformat()
        return datetime.datetime.now(datetime.timezone.utc).isoformat()

    def get_configured_feeds(self) -> list[dict[str, str]]:
        """Combines built-in verified Turkish RSS feeds with any custom feeds configured via settings."""
        feeds: list[dict[str, str]] = list(TURKISH_NEWS_RSS_FEEDS)
        custom = getattr(settings, "rss_custom_feeds", []) or []
        for cf in custom:
            cf_url = cf.strip() if isinstance(cf, str) else ""
            if cf_url and not any(f["url"] == cf_url for f in feeds):
                feeds.append({
                    "name": f"Özel Kaynak ({cf_url[:30]})",
                    "url": cf_url,
                    "category": "Gündem",
                })
        return feeds

    def sanitize_text(self, text: str | None) -> str:
        """Sanitizes text by unescaping HTML entities and removing HTML markup."""
        if not text:
            return ""
        unescaped = html.unescape(text.strip())
        return strip_html_tags(unescaped).strip()

    def _extract_image_url(self, item_node: Any, raw_desc: str) -> str | None:
        """Extracts media/enclosure/thumbnail image URL from XML node or description HTML."""
        try:
            # 1. <enclosure type="image/..." url="..." />
            enclosure = item_node.find("enclosure")
            if enclosure is not None:
                url = enclosure.attrib.get("url", "")
                enc_type = enclosure.attrib.get("type", "")
                if url and ("image" in enc_type or url.endswith((".jpg", ".jpeg", ".png", ".webp", ".avif"))):
                    return url

            # 2. <media:content url="..." />
            for el in item_node.findall(".//{http://search.yahoo.com/mrss/}content"):
                url = el.attrib.get("url", "")
                if url:
                    return url

            # 3. <media:thumbnail url="..." />
            for el in item_node.findall(".//{http://search.yahoo.com/mrss/}thumbnail"):
                url = el.attrib.get("url", "")
                if url:
                    return url
        except Exception:
            pass

        # 4. Regex search in HTML description
        if raw_desc:
            img_match = re.search(r'<img[^>]+src=["\'](https?://[^"\']+)["\']', raw_desc, re.IGNORECASE)
            if img_match:
                return img_match.group(1)

        return None

    def _parse_datetime(self, date_str: str | None) -> datetime.datetime:
        """Parses RFC-822 / ISO 8601 pubDate into timezone-aware datetime."""
        if not date_str:
            return datetime.datetime.now(datetime.timezone.utc)
        try:
            # RFC 2822
            parsed_tuple = email.utils.parsedate_to_datetime(date_str)
            if parsed_tuple:
                if parsed_tuple.tzinfo is None:
                    return parsed_tuple.replace(tzinfo=datetime.timezone.utc)
                return parsed_tuple
        except Exception:
            pass

        try:
            # ISO 8601
            dt = datetime.datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                return dt.replace(tzinfo=datetime.timezone.utc)
            return dt
        except Exception:
            pass

        return datetime.datetime.now(datetime.timezone.utc)

    def _clean_xml_text(self, text_content: str) -> str:
        """Sanitizes raw XML string by escaping unencoded ampersands and removing control chars."""
        # Remove XML-invalid control characters
        cleaned = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", text_content)
        # Replace common HTML named entities that break standard XML parsers
        named_entities = {
            "&nbsp;": " ",
            "&ccedil;": "ç",
            "&Ccedil;": "Ç",
            "&ouml;": "ö",
            "&Ouml;": "Ö",
            "&uuml;": "ü",
            "&Uuml;": "Ü",
            "&scedil;": "ş",
            "&Scedil;": "Ş",
            "&gbreve;": "ğ",
            "&Gbreve;": "Ğ",
            "&inodot;": "ı",
            "&Idot;": "İ",
            "&rsquo;": "'",
            "&lsquo;": "'",
            "&rdquo;": '"',
            "&ldquo;": '"',
            "&hellip;": "...",
            "&ndash;": "-",
            "&mdash;": "-",
            "&amp;": "&amp;",
        }
        for entity, repl in named_entities.items():
            if entity != "&amp;":
                cleaned = cleaned.replace(entity, repl)

        # Fix unescaped ampersands not part of a valid XML entity
        cleaned = re.sub(r"&(?!(amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)", "&amp;", cleaned)
        return cleaned

    def parse_rss_xml(
        self,
        xml_content: bytes | str,
        source_name: str,
        default_category: str = "Gündem",
        source_url: str = "",
    ) -> list[dict[str, Any]]:
        """Parses RSS 2.0 / Atom XML bytes or string into structured records with robust encoding resilience."""
        import xml.etree.ElementTree as ET

        items: list[dict[str, Any]] = []
        if not xml_content:
            return items

        # Quick HTML check: if this is a standard HTML document rather than RSS/Atom feed, return empty
        if isinstance(xml_content, bytes):
            preview = xml_content[:300].lower()
            if b"<!doctype html" in preview or b"<html" in preview:
                return items
        elif isinstance(xml_content, str):
            preview = xml_content[:300].lower()
            if "<!doctype html" in preview or "<html" in preview:
                return items

        root = None
        raw_bytes = xml_content if isinstance(xml_content, bytes) else xml_content.encode("utf-8")

        # 1. If declared encoding is not UTF-8 (e.g. ISO-8859-9, Windows-1254), decode with target charset first
        declared_enc = None
        enc_match = re.search(rb'encoding=["\']([^"\']+)["\']', raw_bytes[:120], re.IGNORECASE)
        if enc_match:
            try:
                declared_enc = enc_match.group(1).decode("ascii", errors="ignore").strip().lower()
            except Exception:
                pass

        if declared_enc and declared_enc not in ("utf-8", "utf8", "ascii", "us-ascii"):
            try:
                text_content = raw_bytes.decode(declared_enc)
                cleaned = self._clean_xml_text(text_content)
                cleaned = re.sub(r'encoding=["\'][^"\']+["\']', 'encoding="utf-8"', cleaned, flags=re.IGNORECASE)
                root = ET.fromstring(cleaned.encode("utf-8"))
            except Exception:
                root = None

        # 2. Try standard XML parsing from bytes
        if root is None:
            try:
                root = ET.fromstring(raw_bytes)
            except Exception:
                pass

        # 3. Try with text decoding and entity cleanup across candidate encodings
        if root is None:
            candidate_encodings = []
            if declared_enc:
                candidate_encodings.append(declared_enc)
            for enc in ("utf-8", "iso-8859-9", "windows-1254", "latin-1", "cp1254"):
                if enc not in candidate_encodings:
                    candidate_encodings.append(enc)

            # First pass: try strict decoding
            for enc in candidate_encodings:
                try:
                    text_content = raw_bytes.decode(enc)
                    cleaned = self._clean_xml_text(text_content)
                    cleaned = re.sub(r'encoding=["\'][^"\']+["\']', 'encoding="utf-8"', cleaned, flags=re.IGNORECASE)
                    root = ET.fromstring(cleaned.encode("utf-8"))
                    if root is not None:
                        break
                except Exception:
                    continue

            # Second pass: replace errors if strict decoding did not produce a root
            if root is None:
                for enc in candidate_encodings:
                    try:
                        text_content = raw_bytes.decode(enc, errors="replace")
                        cleaned = self._clean_xml_text(text_content)
                        cleaned = re.sub(r'encoding=["\'][^"\']+["\']', 'encoding="utf-8"', cleaned, flags=re.IGNORECASE)
                        root = ET.fromstring(cleaned.encode("utf-8"))
                        if root is not None:
                            break
                    except Exception:
                        continue

        if root is None:
            # 4. Emergency regex parser for XML items if ElementTree failed
            return self._regex_fallback_parse(raw_bytes, source_name, default_category, source_url)

        # 1. RSS 2.0 (<item>)
        for item_node in root.findall(".//item"):
            try:
                raw_title = item_node.findtext("title") or "Başlıksız Haber"
                raw_desc = (
                    item_node.findtext("description")
                    or item_node.findtext("{http://purl.org/rss/1.0/modules/content/}encoded")
                    or ""
                )
                link = (item_node.findtext("link") or "").strip()
                raw_pub_date = item_node.findtext("pubDate")
                pub_dt = self._parse_datetime(raw_pub_date)

                title = self.sanitize_text(raw_title)
                summary = self.sanitize_text(raw_desc)
                if not summary or len(summary) < 5:
                    summary = title

                if not title and not summary:
                    continue

                image_url = self._extract_image_url(item_node, raw_desc)
                norm_title = normalize_title(title)
                c_hash = calculate_content_hash(summary, title)
                content_id = f"rss-{c_hash[:12]}"

                items.append({
                    "id": content_id,
                    "content_id": content_id,
                    "title": title[:300],
                    "text": summary[:4000],
                    "summary": summary[:4000],
                    "url": link,
                    "link": link,
                    "original_url": link,
                    "source": source_name,
                    "source_name": source_name,
                    "source_url": source_url,
                    "author": source_name,
                    "category": default_category,
                    "image_url": image_url,
                    "published_at": pub_dt.isoformat(),
                    "published_datetime": pub_dt,
                    "normalized_title": norm_title,
                    "content_hash": c_hash,
                    "time": "Az önce",
                })
            except Exception as item_err:
                logger.debug("Error parsing item in %s: %s", source_name, item_err)
                continue

        # 2. Atom Feed (<entry>)
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
                raw_pub_date = (
                    entry_node.findtext(f"{atom_ns}published")
                    or entry_node.findtext(f"{atom_ns}updated")
                )
                pub_dt = self._parse_datetime(raw_pub_date)

                title = self.sanitize_text(raw_title)
                summary = self.sanitize_text(raw_summary)
                if not summary:
                    summary = title

                norm_title = normalize_title(title)
                c_hash = calculate_content_hash(summary, title)
                content_id = f"atom-{c_hash[:12]}"

                items.append({
                    "id": content_id,
                    "content_id": content_id,
                    "title": title[:300],
                    "text": summary[:4000],
                    "summary": summary[:4000],
                    "url": link,
                    "link": link,
                    "original_url": link,
                    "source": source_name,
                    "source_name": source_name,
                    "source_url": source_url,
                    "author": source_name,
                    "category": default_category,
                    "image_url": None,
                    "published_at": pub_dt.isoformat(),
                    "published_datetime": pub_dt,
                    "normalized_title": norm_title,
                    "content_hash": c_hash,
                    "time": "Az önce",
                })
            except Exception as entry_err:
                logger.debug("Error parsing entry in %s: %s", source_name, entry_err)
                continue

        return items

    def _regex_fallback_parse(
        self,
        raw_bytes: bytes,
        source_name: str,
        default_category: str,
        source_url: str,
    ) -> list[dict[str, Any]]:
        """Fallback regex extractor for slightly malformed XML documents."""
        items: list[dict[str, Any]] = []
        try:
            text_content = raw_bytes.decode("utf-8", errors="replace")
            # Extract item blocks
            item_blocks = re.findall(r"<item>(.*?)</item>", text_content, re.DOTALL | re.IGNORECASE)
            for block in item_blocks:
                title_match = re.search(r"<title>(.*?)</title>", block, re.DOTALL | re.IGNORECASE)
                desc_match = re.search(r"<description>(.*?)</description>", block, re.DOTALL | re.IGNORECASE)
                link_match = re.search(r"<link>(.*?)</link>", block, re.DOTALL | re.IGNORECASE)
                date_match = re.search(r"<pubDate>(.*?)</pubDate>", block, re.DOTALL | re.IGNORECASE)

                raw_title = title_match.group(1) if title_match else ""
                raw_desc = desc_match.group(1) if desc_match else ""
                link = link_match.group(1).strip() if link_match else ""
                raw_date = date_match.group(1).strip() if date_match else None

                title = self.sanitize_text(raw_title)
                summary = self.sanitize_text(raw_desc)
                if not summary:
                    summary = title
                if not title and not summary:
                    continue

                pub_dt = self._parse_datetime(raw_date)
                norm_title = normalize_title(title)
                c_hash = calculate_content_hash(summary, title)
                content_id = f"rss-fallback-{c_hash[:12]}"

                items.append({
                    "id": content_id,
                    "content_id": content_id,
                    "title": title[:300],
                    "text": summary[:4000],
                    "summary": summary[:4000],
                    "url": link,
                    "link": link,
                    "original_url": link,
                    "source": source_name,
                    "source_name": source_name,
                    "source_url": source_url,
                    "author": source_name,
                    "category": default_category,
                    "image_url": None,
                    "published_at": pub_dt.isoformat(),
                    "published_datetime": pub_dt,
                    "normalized_title": norm_title,
                    "content_hash": c_hash,
                    "time": "Az önce",
                })
        except Exception as e:
            logger.debug("Regex fallback parser failed for %s: %s", source_name, e)
        return items

    def fetch_feed(self, source_info: dict[str, str] | str) -> list[dict[str, Any]]:
        """Fetches a single remote RSS feed with timeout, retry backoff, and user-agent headers."""
        if isinstance(source_info, str):
            url = source_info
            name = "Haber Kaynağı"
            category = "Gündem"
            for src in TURKISH_NEWS_RSS_FEEDS:
                if src["url"] == url:
                    name = src["name"]
                    category = src["category"]
                    break
        else:
            name = source_info.get("name", "Haber Kaynağı")
            url = source_info.get("url", "")
            category = source_info.get("category", "Gündem")

        if not url:
            return []

        headers = {
            "User-Agent": USER_AGENT,
            "Accept": ACCEPT_HEADER,
        }

        # 2 attempts with safe exponential backoff
        for attempt in range(1, 3):
            try:
                with httpx.Client(
                    timeout=httpx.Timeout(self.timeout_seconds, connect=5.0),
                    follow_redirects=True,
                    headers=headers,
                ) as client:
                    resp = client.get(url)
                    status_code = resp.status_code

                    if status_code == 200:
                        content_type = resp.headers.get("content-type", "").lower()
                        # If server returned an HTML error/landing page, log and return empty
                        if ("text/html" in content_type and b"<!doctype html" in resp.content[:300].lower()):
                            logger.info("[RSS Feed] Source: '%s' | URL: %s | Status: 200 | Items: 0 | Error: HTML_PAGE_DETECTED", name, url)
                            return []

                        items = self.parse_rss_xml(resp.content, source_name=name, default_category=category, source_url=url)
                        logger.info("[RSS Feed] Source: '%s' | URL: %s | Status: %d | Items: %d | Error: None", name, url, status_code, len(items))
                        return items
                    else:
                        logger.warning("[RSS Feed] Source: '%s' | URL: %s | Status: %d | Items: 0 | Error: HTTPStatusError", name, url, status_code)
                        return []

            except httpx.ConnectTimeout:
                if attempt == 1:
                    time.sleep(0.3)
                else:
                    logger.warning("[RSS Feed] Source: '%s' | URL: %s | Status: None | Items: 0 | Error: ConnectTimeout", name, url)
            except httpx.ReadTimeout:
                if attempt == 1:
                    time.sleep(0.3)
                else:
                    logger.warning("[RSS Feed] Source: '%s' | URL: %s | Status: None | Items: 0 | Error: ReadTimeout", name, url)
            except httpx.HTTPStatusError as e:
                logger.warning("[RSS Feed] Source: '%s' | URL: %s | Status: %s | Items: 0 | Error: HTTPStatusError", name, url, getattr(e.response, "status_code", "unknown"))
                return []
            except Exception as e:
                err_class = type(e).__name__
                if attempt == 1:
                    time.sleep(0.3)
                else:
                    logger.warning("[RSS Feed] Source: '%s' | URL: %s | Status: None | Items: 0 | Error: %s", name, url, err_class)

        return []

    def fetch_all_feeds(self, force_refresh: bool = False) -> list[dict[str, Any]]:
        """Fetches all Turkish RSS feeds concurrently with ThreadPoolExecutor, interleaves results, and deduplicates in-memory."""
        now = time.time()
        if not force_refresh and self._cached_items and (now - self._last_fetched < self.cache_ttl_seconds):
            return self._cached_items

        all_sources = self.get_configured_feeds()
        all_feed_results: list[list[dict[str, Any]]] = []

        with ThreadPoolExecutor(max_workers=20) as executor:
            fetched_lists = list(executor.map(self.fetch_feed, all_sources))

        for items in fetched_lists:
            if items and len(items) > 0:
                all_feed_results.append(items)

        # Interleave items from different sources for a rich, balanced multi-category stream
        combined: list[dict[str, Any]] = []
        max_len = max((len(lst) for lst in all_feed_results), default=0)
        for i in range(max_len):
            for feed_list in all_feed_results:
                if i < len(feed_list):
                    combined.append(feed_list[i])

        # In-memory deduplicate by url or (title + source)
        seen_keys: set[str] = set()
        unique_posts: list[dict[str, Any]] = []
        for post in combined:
            orig_url = (post.get("original_url") or post.get("url") or "").strip().lower()
            norm_title = post.get("normalized_title") or normalize_title(post.get("title"))
            src = (post.get("source_name") or post.get("source") or "").strip().lower()

            key = orig_url if orig_url else f"{src}_{norm_title}"
            if key not in seen_keys and (post.get("title") or post.get("text")):
                seen_keys.add(key)
                unique_posts.append(post)

        if unique_posts:
            self._cached_items = unique_posts
            self._last_fetched = now
            logger.info("[RSS Service] Fetched and in-memory deduplicated %d live news items from %d active feeds.", len(unique_posts), len(all_feed_results))
            return unique_posts

        return self._cached_items or []

    def ingest_all_sync(self, db_session=None) -> dict[str, Any]:
        """Synchronously fetches from all configured RSS sources, classifies mood with Mood AI,
        and saves unique posts to database with ON CONFLICT / upsert behavior and job locking.
        Never deletes existing archive posts.
        """
        all_sources = self.get_configured_feeds()
        configured_count = len(all_sources)

        # Check if ingestion is enabled in settings
        is_enabled = getattr(settings, "rss_ingestion_enabled", True)
        if not is_enabled:
            logger.info("[RSS Ingestion] Ingestion skipped: RSS_INGESTION_ENABLED is set to false.")
            from backend.db.database import get_storage_mode
            summary = {
                "configured_feed_count": configured_count,
                "feeds_checked": 0,
                "feeds_succeeded": 0,
                "feeds_failed": 0,
                "items_fetched": 0,
                "items_normalized": 0,
                "items_inserted": 0,
                "items_updated": 0,
                "duplicates_skipped": 0,
                "storage_mode": get_storage_mode(),
                "elapsed_seconds": 0.0,
                "errors_summary": "Ingestion disabled by configuration",
                "last_ingested_at": self.last_ingested_at_iso,
            }
            self._last_summary = summary
            return summary

        # Job locking to prevent concurrent ingestions
        with self._ingestion_thread_lock:
            if self._is_ingesting:
                logger.info("[RSS Ingestion] Ingestion already running. Skipping concurrent run.")
                return self._last_summary

            self._is_ingesting = True

        start_time = time.perf_counter()
        feeds_checked = configured_count
        feeds_succeeded = 0
        feeds_failed = 0
        inserted_count = 0
        updated_count = 0
        duplicates_skipped = 0
        total_fetched = 0
        total_normalized = 0
        storage_mode = "unknown"
        sanitized_error: str | None = None

        try:
            from backend.db.database import get_db_session, get_storage_mode
            from backend.database.models import Post, User
            from backend.scoring import get_scorer

            storage_mode = get_storage_mode()
            session = db_session or get_db_session()
            close_session = db_session is None

            try:
                def _safe_fetch(src):
                    try:
                        return self.fetch_feed(src)
                    except Exception as e:
                        logger.warning("[RSS Feed] Feed execution error for %s: %s", src.get("name", ""), e)
                        return []

                # 1. Fetch all feeds concurrently
                with ThreadPoolExecutor(max_workers=20) as executor:
                    fetched_lists = list(executor.map(_safe_fetch, all_sources))

                all_items: list[dict[str, Any]] = []
                for items in fetched_lists:
                    if not items or len(items) == 0:
                        feeds_failed += 1
                    else:
                        feeds_succeeded += 1
                        all_items.extend(items)

                total_fetched = len(all_items)

                # 2. Find or create system bot user
                system_user = session.query(User).filter(User.email == "rss.bot@moodfeed.app").first()
                if not system_user:
                    system_user = session.query(User).first()
                    if not system_user:
                        system_user = User(
                            id=uuid.uuid4(),
                            email="rss.bot@moodfeed.app",
                            username="haber_botu",
                            display_name="Canlı Haber Botu",
                            full_name="MoodFeed RSS Ingestion",
                            avatar="📰",
                            bio="Canlı RSS haber sağlayıcısı.",
                            is_verified=True,
                        )
                        session.add(system_user)
                        session.commit()
                        session.refresh(system_user)

                user_id = system_user.id
                scorer = get_scorer()

                # 3. Build fast lookup maps from DB for dedup without loading entire objects
                existing_urls: set[str] = set(
                    row[0].strip().lower() for row in session.query(Post.original_url).all() if row[0]
                )
                existing_titles: set[str] = set(
                    f"{(row[0] or '').lower()}_{(row[1] or '').lower()}"
                    for row in session.query(Post.source_name, Post.normalized_title).all()
                    if row[1]
                )
                existing_hashes: set[str] = set(
                    row[0] for row in session.query(Post.content_hash).all() if row[0]
                )

                now_utc = datetime.datetime.now(datetime.timezone.utc)

                for item in all_items:
                    title = (item.get("title") or "").strip()
                    text = (item.get("text") or item.get("summary") or title).strip()
                    if not title and not text:
                        continue

                    total_normalized += 1
                    orig_url = (item.get("original_url") or item.get("url") or item.get("link") or "").strip()
                    source_name = item.get("source_name") or item.get("source") or "Haber Kaynağı"
                    category = item.get("category") or "Gündem"
                    image_url = item.get("image_url")
                    pub_dt = item.get("published_datetime") or self._parse_datetime(item.get("published_at"))
                    norm_title = item.get("normalized_title") or normalize_title(title)
                    c_hash = item.get("content_hash") or calculate_content_hash(text, title)

                    url_key = orig_url.lower() if orig_url else None
                    title_key = f"{source_name.lower()}_{norm_title.lower()}"

                    # Deduplication Checks:
                    # 1. Check original_url
                    if url_key and url_key in existing_urls:
                        if image_url:
                            existing_post = session.query(Post).filter(Post.original_url == orig_url).first()
                            if existing_post and not existing_post.image_url:
                                existing_post.image_url = image_url
                                existing_post.updated_at = now_utc
                                updated_count += 1
                                continue
                        duplicates_skipped += 1
                        continue

                    # 2. Check source_name + normalized_title
                    if title_key in existing_titles:
                        duplicates_skipped += 1
                        continue

                    # 3. Check content_hash
                    if c_hash in existing_hashes:
                        duplicates_skipped += 1
                        continue

                    # 4. Insert new Post with 6-class Mood AI scoring
                    mood_res = mood_detector.detect_mood(text, title=title, category=category)
                    cin = ContentInput(id=item.get("id") or str(uuid.uuid4()), text=f"{title}. {text}")
                    analysis = scorer.analyze(cin)

                    post_obj = Post(
                        id=uuid.uuid4(),
                        user_id=user_id,
                        title=title[:300],
                        content=text[:4000],
                        author=source_name,
                        handle="@" + source_name.lower().replace(" ", "").replace(".", "").replace("ı", "i")[:60],
                        category=category,
                        source_name=source_name,
                        source_url=item.get("source_url") or orig_url,
                        original_url=orig_url or None,
                        image_url=image_url,
                        published_at=pub_dt,
                        fetched_at=now_utc,
                        normalized_title=norm_title[:255],
                        content_hash=c_hash,
                        mood_score=mood_res["mood_score"],
                        mood_label=mood_res["mood_label"],
                        mood_distribution=mood_res["mood_distribution"],
                        sentiment_label=mood_res["sentiment"]["label"],
                        sentiment_score=mood_res["sentiment"]["score"],
                        negativity_score=max(mood_res["negativity_score"], analysis.negativity_score),
                        toxicity_score=max(mood_res["toxicity_score"], analysis.toxicity_score),
                        spam_score=0.0,
                        bot_risk="low",
                        repetition_score=0.0,
                        language="tr",
                        metadata_json={
                            "source_category": category,
                            "confidence": mood_res["mood_distribution"].get("confidence", 0.7),
                            "image_url": image_url,
                        },
                        is_published=True,
                        created_at=now_utc,
                        updated_at=now_utc,
                    )
                    session.add(post_obj)

                    if url_key:
                        existing_urls.add(url_key)
                    existing_titles.add(title_key)
                    existing_hashes.add(c_hash)
                    inserted_count += 1

                session.commit()

                # 5. Run Retention Cleanup (default: 90 days)
                self.run_retention_cleanup(db_session=session)

                self._last_ingested_at = now_utc
                self._last_error = None
            except Exception as db_err:
                session.rollback()
                sanitized_error = f"{type(db_err).__name__}: {str(db_err)[:100]}"
                self._last_error = sanitized_error
                logger.warning("[RSS Ingestion] Database transaction error: %s", sanitized_error)
            finally:
                if close_session:
                    try:
                        session.close()
                    except Exception:
                        pass

        except Exception as e:
            sanitized_error = f"{type(e).__name__}: {str(e)[:100]}"
            self._last_error = sanitized_error
            logger.warning("[RSS Ingestion] Ingestion pipeline error: %s", sanitized_error)
        finally:
            with self._ingestion_thread_lock:
                self._is_ingesting = False

        duration = round(time.perf_counter() - start_time, 2)
        summary = {
            "configured_feed_count": configured_count,
            "feeds_checked": feeds_checked,
            "feeds_succeeded": feeds_succeeded,
            "feeds_failed": feeds_failed,
            "failed_feeds": feeds_failed,
            "items_fetched": total_fetched,
            "fetched_items": total_fetched,
            "items_normalized": total_normalized,
            "items_inserted": inserted_count,
            "inserted": inserted_count,
            "items_updated": updated_count,
            "updated": updated_count,
            "duplicates_skipped": duplicates_skipped,
            "storage_mode": storage_mode,
            "elapsed_seconds": duration,
            "duration_seconds": duration,
            "errors_summary": sanitized_error,
            "last_ingested_at": self.last_ingested_at_iso,
        }
        self._last_summary = summary

        # 1. Single-line structured log with exact key-value specifications
        logger.info(
            "RSS ingestion completed: "
            "configured_feed_count=%d, "
            "feeds_checked=%d, "
            "feeds_succeeded=%d, "
            "feeds_failed=%d, "
            "items_fetched=%d, "
            "items_normalized=%d, "
            "items_inserted=%d, "
            "items_updated=%d, "
            "duplicates_skipped=%d, "
            "storage_mode=%s, "
            "elapsed_seconds=%.2f, "
            "errors=%s",
            configured_count,
            feeds_checked,
            feeds_succeeded,
            feeds_failed,
            total_fetched,
            total_normalized,
            inserted_count,
            updated_count,
            duplicates_skipped,
            storage_mode,
            duration,
            sanitized_error or "none",
        )

        # 2. Multi-line structured summary log
        logger.info(
            "RSS ingestion summary:\n"
            "- configured_feed_count: %d\n"
            "- feeds_checked: %d\n"
            "- feeds_succeeded: %d\n"
            "- feeds_failed: %d\n"
            "- items_fetched: %d\n"
            "- items_normalized: %d\n"
            "- items_inserted: %d\n"
            "- items_updated: %d\n"
            "- duplicates_skipped: %d\n"
            "- storage_mode: %s\n"
            "- elapsed_seconds: %.2f\n"
            "- errors_summary: %s",
            configured_count,
            feeds_checked,
            feeds_succeeded,
            feeds_failed,
            total_fetched,
            total_normalized,
            inserted_count,
            updated_count,
            duplicates_skipped,
            storage_mode,
            duration,
            sanitized_error or "none",
        )

        return summary

    async def ingest_all(self, db_session=None) -> dict[str, Any]:
        """Asynchronously ingests, classifies, and archives news posts."""
        if self._async_lock is None:
            self._async_lock = asyncio.Lock()

        if self._async_lock.locked():
            logger.info("[RSS Ingestion] Async lock is held. Skipping overlapping ingestion.")
            return self._last_summary

        async with self._async_lock:
            return await asyncio.to_thread(self.ingest_all_sync, db_session)

    async def ingest_all_async(self, db_session=None) -> dict[str, Any]:
        """Alias for async ingest_all."""
        return await self.ingest_all(db_session)

    async def fetch_all_sources(self, force_refresh: bool = False) -> list[dict[str, Any]]:
        """Asynchronously fetches all Turkish news RSS sources."""
        return await asyncio.to_thread(self.fetch_all_feeds, force_refresh)

    def run_retention_cleanup(self, days: int = 90, db_session=None) -> int:
        """Deletes posts older than retention days threshold (default: 90 days)."""
        retention_days = days or getattr(settings, "data_retention_days", 90)
        if retention_days <= 0:
            return 0

        try:
            from backend.db.database import get_db_session
            from backend.database.models import Post

            session = db_session or get_db_session()
            close_session = db_session is None

            try:
                now_utc = datetime.datetime.now(datetime.timezone.utc)
                cutoff_aware = now_utc - datetime.timedelta(days=retention_days)
                cutoff_naive = cutoff_aware.replace(tzinfo=None)

                # Fetch candidate posts and evaluate retention cutoff
                all_candidates = session.query(Post).all()
                posts_to_delete = []
                for p in all_candidates:
                    if p.author == "Kullanıcı":
                        continue
                    p_time = p.created_at or p.published_at
                    if not p_time:
                        continue
                    if isinstance(p_time, str):
                        try:
                            p_time = datetime.datetime.fromisoformat(p_time.replace("Z", "+00:00"))
                        except Exception:
                            continue
                    if isinstance(p_time, datetime.datetime):
                        if p_time.tzinfo is None:
                            if p_time < cutoff_naive:
                                posts_to_delete.append(p)
                        else:
                            if p_time < cutoff_aware:
                                posts_to_delete.append(p)

                deleted_count = len(posts_to_delete)
                for p in posts_to_delete:
                    session.delete(p)
                session.commit()

                if deleted_count > 0:
                    logger.info("[Retention] Cleaned up %d posts older than %d days.", deleted_count, retention_days)
                return deleted_count
            finally:
                if close_session:
                    try:
                        session.close()
                    except Exception:
                        pass
        except Exception as e:
            logger.warning("[Retention] Cleanup error: %s", e)
            return 0

    def get_stats(self, db_session=None) -> dict[str, Any]:
        """Returns accurate database metrics for total posts, mood breakdown, and category stats."""
        try:
            from backend.db.database import get_db_session
            from backend.database.models import Post
            from sqlalchemy import func

            session = db_session or get_db_session()
            close_session = db_session is None

            try:
                now = datetime.datetime.now(datetime.timezone.utc)
                today_start = datetime.datetime(now.year, now.month, now.day, tzinfo=datetime.timezone.utc)

                total_posts = session.query(Post).filter(Post.is_published.is_(True)).count()
                posts_today = session.query(Post).filter(Post.is_published.is_(True), Post.created_at >= today_start).count()

                # Group by mood
                mood_counts = {
                    "calm": 0,
                    "happy": 0,
                    "neutral": 0,
                    "anxious": 0,
                    "sad": 0,
                    "angry": 0,
                }
                mood_rows = session.query(Post.mood_label, func.count(Post.id)).filter(Post.is_published.is_(True)).group_by(Post.mood_label).all()
                for label, count in mood_rows:
                    if label and label.lower() in mood_counts:
                        mood_counts[label.lower()] = count

                # Group by category
                cat_rows = session.query(Post.category, func.count(Post.id)).filter(Post.is_published.is_(True)).group_by(Post.category).all()
                posts_by_category = {cat: count for cat, count in cat_rows if cat}

                return {
                    "total_posts": total_posts,
                    "today_posts": posts_today,
                    "posts_today": posts_today,
                    "posts_by_mood": mood_counts,
                    "posts_by_category": posts_by_category,
                    "last_ingested_at": self.last_ingested_at_iso,
                    "last_updated": now.isoformat(),
                    "last_ingestion_summary": self.last_summary,
                }
            finally:
                if close_session:
                    try:
                        session.close()
                    except Exception:
                        pass
        except Exception as e:
            logger.warning("[RSS Stats] Error computing stats: %s", e)
            return {
                "total_posts": 0,
                "today_posts": 0,
                "posts_today": 0,
                "posts_by_mood": {"calm": 0, "happy": 0, "neutral": 0, "anxious": 0, "sad": 0, "angry": 0},
                "posts_by_category": {},
                "last_ingested_at": self.last_ingested_at_iso,
                "last_updated": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "last_ingestion_summary": self.last_summary,
            }

    @property
    def all_items(self) -> list[dict[str, Any]]:
        """Returns currently cached feed items."""
        return self._cached_items

    def get_live_content_inputs(self, limit: int = 100) -> list[ContentInput]:
        """Converts archived posts or fetched RSS news items into ContentInput models for reranking."""
        try:
            from backend.db.database import get_db_session
            from backend.database.models import Post

            session = get_db_session()
            try:
                db_posts = (
                    session.query(Post)
                    .filter(Post.is_published.is_(True))
                    .order_by(Post.published_at.desc(), Post.created_at.desc())
                    .limit(limit)
                    .all()
                )
                if db_posts:
                    inputs: list[ContentInput] = []
                    for idx, p in enumerate(db_posts, start=1):
                        initial_score = round(max(0.40, min(0.95, 0.75 - (idx * 0.002))), 3)
                        inputs.append(
                            ContentInput(
                                id=str(p.id),
                                text=f"{p.title}. {p.content}" if p.title and p.title not in p.content else p.content,
                                original_score=initial_score,
                                title=p.title or "",
                                url=p.original_url or p.source_url or "",
                                source=p.source_name or p.author or "Haber Kaynağı",
                                author=p.author or p.source_name or "Haber Kaynağı",
                                category=p.category or "Gündem",
                                published_at=p.published_at.isoformat() if p.published_at else (p.created_at.isoformat() if p.created_at else None),
                            )
                        )
                    return inputs
            finally:
                session.close()
        except Exception as e:
            logger.debug("Failed to read from DB for live inputs, falling back to cache: %s", e)

        raw_items = self.fetch_all_feeds()
        if not raw_items:
            return []

        content_inputs: list[ContentInput] = []
        for idx, item in enumerate(raw_items[:limit], start=1):
            try:
                initial_score = max(0.40, min(0.95, round(0.75 - (idx * 0.002), 3)))
                clean_title = (item.get("title") or "").strip()
                clean_summary = (item.get("summary") or item.get("text") or "").strip()
                combined_text = f"{clean_title}. {clean_summary}".strip() if clean_title and clean_summary != clean_title else (clean_title or clean_summary or "Haber içeriği")

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
            except Exception:
                continue

        return content_inputs


# Singleton RSS service instance
rss_service = RSSService()
RSSIngestionService = RSSService
