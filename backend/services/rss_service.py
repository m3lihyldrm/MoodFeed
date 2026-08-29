"""MoodFeed Live Turkish News RSS Aggregation & Persistent Archive Service.

Fetches, normalizes, deduplicates, and persists news feeds from 40+ Turkish sources
across 10 core categories (Gündem, Dünya, Ekonomi, Teknoloji, Bilim, Kültür/Sanat, Spor, Sağlık, Çevre/İklim, Eğitim).
Features:
- Never deletes existing valid records on ingestion (incremental archiving).
- Strict multi-tier deduplication (original_url -> normalized_title+source -> content_hash).
- 6-class Mood AI classification (calm, happy, neutral, anxious, sad, angry).
- Ingestion job locking to prevent concurrent runs.
- Automated data retention cleanup (default 90 days).
- Comprehensive structured logging and real-time metrics.
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
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from typing import Any
import uuid

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
    {"name": "TRT Haber", "url": "https://www.trthaber.com/rss.php", "category": "Gündem"},
    {"name": "TRT Gündem", "url": "https://www.trthaber.com/gundem_articles.rss", "category": "Gündem"},
    {"name": "TRT Manşet", "url": "https://www.trthaber.com/manset_articles.rss", "category": "Gündem"},
    {"name": "TRT Son Dakika", "url": "https://www.trthaber.com/sondakika_articles.rss", "category": "Gündem"},
    {"name": "NTV Haber", "url": "https://www.ntv.com.tr/rss", "category": "Gündem"},
    {"name": "NTV Gündem", "url": "https://www.ntv.com.tr/gundem.rss", "category": "Gündem"},
    {"name": "NTV Türkiye", "url": "https://www.ntv.com.tr/turkiye.rss", "category": "Gündem"},
    {"name": "HaberTürk RSS", "url": "https://www.haberturk.com/rss", "category": "Gündem"},
    {"name": "HaberTürk Manşet", "url": "https://www.haberturk.com/rss/manset.xml", "category": "Gündem"},
    {"name": "HaberTürk Gündem", "url": "https://www.haberturk.com/rss/kategori/gundem.xml", "category": "Gündem"},
    {"name": "Sözcü", "url": "https://www.sozcu.com.tr/feed/", "category": "Gündem"},
    {"name": "Sözcü Gündem", "url": "https://www.sozcu.com.tr/feeds-haberler", "category": "Gündem"},
    {"name": "Milliyet", "url": "https://www.milliyet.com.tr/rss/", "category": "Gündem"},
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
    {"name": "VOA Türkçe", "url": "https://www.voaturkce.com/api/z", "category": "Dünya"},
    {"name": "NTV Dünya", "url": "https://www.ntv.com.tr/dunya.rss", "category": "Dünya"},
    {"name": "Hürriyet Dünya", "url": "https://www.hurriyet.com.tr/rss/dunya", "category": "Dünya"},
    {"name": "TRT Dünya", "url": "https://www.trthaber.com/dunya_articles.rss", "category": "Dünya"},

    # 3. EKONOMİ & FİNANS
    {"name": "Para Analiz", "url": "https://www.paraanaliz.com/rss", "category": "Ekonomi"},
    {"name": "Döviz.com", "url": "https://www.doviz.com/rss", "category": "Ekonomi"},
    {"name": "Altın.in", "url": "https://www.altin.in/rss", "category": "Ekonomi"},
    {"name": "TRT Ekonomi", "url": "https://www.trthaber.com/ekonomi_articles.rss", "category": "Ekonomi"},
    {"name": "NTV Ekonomi", "url": "https://www.ntv.com.tr/ekonomi.rss", "category": "Ekonomi"},
    {"name": "HaberTürk Ekonomi", "url": "https://www.haberturk.com/rss/kategori/ekonomi.xml", "category": "Ekonomi"},
    {"name": "Hürriyet Ekonomi", "url": "https://www.hurriyet.com.tr/rss/ekonomi", "category": "Ekonomi"},
    {"name": "Cumhuriyet Ekonomi", "url": "https://www.cumhuriyet.com.tr/rss/ekonomi.xml", "category": "Ekonomi"},
    {"name": "BloombergHT", "url": "https://www.bloomberght.com/rss", "category": "Ekonomi"},
    {"name": "Dünya Gazetesi", "url": "https://www.dunya.com/rss", "category": "Ekonomi"},

    # 4. TEKNOLOJİ
    {"name": "Webtekno", "url": "https://www.webtekno.com/rss/", "category": "Teknoloji"},
    {"name": "Webtekno XML", "url": "https://www.webtekno.com/rss.xml", "category": "Teknoloji"},
    {"name": "ShiftDelete.Net", "url": "https://www.shiftdelete.net/feed/", "category": "Teknoloji"},
    {"name": "DonanımHaber", "url": "https://www.donanimhaber.com/rss/", "category": "Teknoloji"},
    {"name": "DonanımHaber Tüm", "url": "https://www.donanimhaber.com/rss/tum/", "category": "Teknoloji"},
    {"name": "TRT Bilim Teknoloji", "url": "https://www.trthaber.com/bilim_teknoloji_articles.rss", "category": "Teknoloji"},
    {"name": "NTV Teknoloji", "url": "https://www.ntv.com.tr/teknoloji.rss", "category": "Teknoloji"},
    {"name": "HaberTürk Teknoloji", "url": "https://www.haberturk.com/rss/kategori/teknoloji.xml", "category": "Teknoloji"},
    {"name": "Hürriyet Teknoloji", "url": "https://www.hurriyet.com.tr/rss/teknoloji", "category": "Teknoloji"},
    {"name": "Webrazzi", "url": "https://webrazzi.com/feed/", "category": "Teknoloji"},
    {"name": "Chip Online", "url": "https://www.chip.com.tr/rss/", "category": "Teknoloji"},

    # 5. BİLİM & KEŞİF
    {"name": "TRT Bilim", "url": "https://www.trthaber.com/bilim_articles.rss", "category": "Bilim"},
    {"name": "Evrim Ağacı", "url": "https://evrimagaci.org/rss.xml", "category": "Bilim"},
    {"name": "Arkeofili", "url": "https://arkeofili.com/feed/", "category": "Bilim"},

    # 6. KÜLTÜR & SANAT
    {"name": "TRT Kültür Sanat", "url": "https://www.trthaber.com/kultur_sanat_articles.rss", "category": "Kültür"},
    {"name": "Hürriyet Kültür Sanat", "url": "https://www.hurriyet.com.tr/rss/kultur-sanat", "category": "Kültür"},
    {"name": "NTV Sanat", "url": "https://www.ntv.com.tr/sanat.rss", "category": "Kültür"},

    # 7. SPOR
    {"name": "Fanatik", "url": "https://www.fanatik.com.tr/rss", "category": "Spor"},
    {"name": "Sporx", "url": "https://www.sporx.com/rss", "category": "Spor"},
    {"name": "90min Türkçe", "url": "https://www.90min.com.tr/rss", "category": "Spor"},
    {"name": "TRT Spor", "url": "https://www.trthaber.com/spor_articles.rss", "category": "Spor"},
    {"name": "NTV Spor", "url": "https://www.ntv.com.tr/sporskor.rss", "category": "Spor"},
    {"name": "HaberTürk Spor", "url": "https://www.haberturk.com/rss/kategori/spor.xml", "category": "Spor"},
    {"name": "Hürriyet Spor", "url": "https://www.hurriyet.com.tr/rss/spor", "category": "Spor"},
    {"name": "Fotomaç", "url": "https://www.fotomac.com.tr/rss/anasayfa.xml", "category": "Spor"},

    # 8. SAĞLIK & YAŞAM
    {"name": "TRT Sağlık", "url": "https://www.trthaber.com/saglik_articles.rss", "category": "Sağlık"},
    {"name": "NTV Sağlık", "url": "https://www.ntv.com.tr/saglik.rss", "category": "Sağlık"},
    {"name": "Hürriyet Sağlık", "url": "https://www.hurriyet.com.tr/rss/saglik", "category": "Sağlık"},

    # 9. ÇEVRE & İKLİM
    {"name": "TRT Çevre", "url": "https://www.trthaber.com/cevre_articles.rss", "category": "Çevre"},
    {"name": "Yeşil Gazete", "url": "https://yesilgazete.org/feed/", "category": "Çevre"},
    {"name": "İklim Haber", "url": "https://www.iklimhaber.org/feed/", "category": "Çevre"},

    # 10. EĞİTİM
    {"name": "TRT Eğitim", "url": "https://www.trthaber.com/egitim_articles.rss", "category": "Eğitim"},
    {"name": "Hürriyet Eğitim", "url": "https://www.hurriyet.com.tr/rss/egitim", "category": "Eğitim"},
]

# Backward-compatibility flat URL list
RSS_FEEDS = [src["url"] for src in TURKISH_NEWS_RSS_FEEDS]


class RSSService:
    """Production RSS Service for live news feed ingestion, deduplication, and persistent archiving."""

    def __init__(self, cache_ttl_seconds: int = 45, timeout_seconds: int = 6) -> None:
        self.cache_ttl_seconds = cache_ttl_seconds
        self.timeout_seconds = timeout_seconds
        self._cached_items: list[dict[str, Any]] = []
        self._last_fetched: float = 0.0
        self._last_ingested_at: datetime.datetime | None = None
        self._is_ingesting: bool = False
        self._ingestion_thread_lock = threading.Lock()
        self._async_lock: asyncio.Lock | None = None
        self._last_summary: dict[str, Any] = {
            "feeds_checked": 0,
            "fetched_items": 0,
            "inserted": 0,
            "updated": 0,
            "duplicates_skipped": 0,
            "failed_feeds": 0,
            "duration_seconds": 0.0,
        }

    @property
    def last_summary(self) -> dict[str, Any]:
        return dict(self._last_summary)

    @property
    def last_ingested_at_iso(self) -> str:
        if self._last_ingested_at:
            return self._last_ingested_at.isoformat()
        return datetime.datetime.now(datetime.timezone.utc).isoformat()

    def sanitize_text(self, text: str | None) -> str:
        """Sanitizes text by unescaping HTML entities and removing HTML markup."""
        if not text:
            return ""
        unescaped = html.unescape(text.strip())
        return strip_html_tags(unescaped).strip()

    def _extract_image_url(self, item_node: ET.Element, raw_desc: str) -> str | None:
        """Extracts media/enclosure/thumbnail image URL from XML node or description HTML."""
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

    def parse_rss_xml(
        self,
        xml_bytes: bytes,
        source_name: str,
        default_category: str = "Gündem",
        source_url: str = "",
    ) -> list[dict[str, Any]]:
        """Parses RSS 2.0 / Atom XML bytes into clean structured records with encoding resilience."""
        items: list[dict[str, Any]] = []
        root = None

        try:
            root = ET.fromstring(xml_bytes)
        except Exception:
            for enc in ("utf-8", "latin-1", "iso-8859-9", "windows-1254"):
                try:
                    text_content = xml_bytes.decode(enc, errors="replace")
                    text_content = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", text_content)
                    root = ET.fromstring(text_content)
                    if root is not None:
                        break
                except Exception:
                    continue

        if root is None:
            return items

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

        # Retry logic: 2 attempts with short exponential backoff
        for attempt in range(1, 3):
            try:
                req = urllib.request.Request(
                    url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 MoodFeed/1.0",
                        "Accept": "application/rss+xml, application/xml, text/xml, application/atom+xml, */*",
                    },
                )
                with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                    if resp.status == 200:
                        data = resp.read()
                        return self.parse_rss_xml(data, source_name=name, default_category=category, source_url=url)
            except Exception as e:
                if attempt == 1:
                    time.sleep(0.3)
                else:
                    logger.debug("[RSS Service] %s feed fetch error (%s): %s", name, url, e)

        return []

    def fetch_all_feeds(self, force_refresh: bool = False) -> list[dict[str, Any]]:
        """Fetches all Turkish RSS feeds concurrently with ThreadPoolExecutor, interleaves results, and deduplicates in-memory."""
        now = time.time()
        if not force_refresh and self._cached_items and (now - self._last_fetched < self.cache_ttl_seconds):
            return self._cached_items

        all_feed_results: list[list[dict[str, Any]]] = []

        with ThreadPoolExecutor(max_workers=25) as executor:
            fetched_lists = list(executor.map(self.fetch_feed, TURKISH_NEWS_RSS_FEEDS))

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
        """Synchronously fetches from all RSS sources, classifies mood with Mood AI,
        and saves unique posts to database with ON CONFLICT / upsert behavior and job locking.
        Never deletes existing archive posts.
        """
        # Job locking to prevent concurrent ingestions
        with self._ingestion_thread_lock:
            if self._is_ingesting:
                logger.info("[RSS Ingestion] Ingestion already running. Skipping concurrent run.")
                return self._last_summary

            self._is_ingesting = True

        start_time = time.perf_counter()
        feeds_checked = len(TURKISH_NEWS_RSS_FEEDS)
        failed_feeds = 0
        inserted_count = 0
        updated_count = 0
        duplicates_skipped = 0
        total_fetched = 0

        try:
            from backend.db.database import SessionLocal, _get_fallback_sessionmaker
            from backend.database.models import Post, User
            from backend.scoring import get_scorer

            session = db_session or (SessionLocal() if callable(SessionLocal) else _get_fallback_sessionmaker()())
            close_session = db_session is None

            try:
                # 1. Fetch all feeds concurrently
                with ThreadPoolExecutor(max_workers=25) as executor:
                    fetched_lists = list(executor.map(self.fetch_feed, TURKISH_NEWS_RSS_FEEDS))

                all_items: list[dict[str, Any]] = []
                for idx, items in enumerate(fetched_lists):
                    if not items:
                        failed_feeds += 1
                    else:
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
                # a) Map by original_url
                existing_urls: set[str] = set(
                    row[0].strip().lower() for row in session.query(Post.original_url).all() if row[0]
                )
                # b) Map by source_name + normalized_title
                existing_titles: set[str] = set(
                    f"{(row[0] or '').lower()}_{(row[1] or '').lower()}"
                    for row in session.query(Post.source_name, Post.normalized_title).all()
                    if row[1]
                )
                # c) Map by content_hash
                existing_hashes: set[str] = set(
                    row[0] for row in session.query(Post.content_hash).all() if row[0]
                )

                now_utc = datetime.datetime.now(datetime.timezone.utc)

                for item in all_items:
                    title = (item.get("title") or "").strip()
                    text = (item.get("text") or item.get("summary") or title).strip()
                    if not title and not text:
                        continue

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
                        # Existing item -> Check if we can update metadata or image_url
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
                        handle="@" + source_name.lower().replace(" ", "").replace(".", "").replace("ı", "i"),
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
            finally:
                if close_session:
                    session.close()

        except Exception as e:
            logger.warning("[RSS Ingestion] Database ingestion error: %s", e)
        finally:
            with self._ingestion_thread_lock:
                self._is_ingesting = False

        duration = round(time.perf_counter() - start_time, 2)
        summary = {
            "feeds_checked": feeds_checked,
            "fetched_items": total_fetched,
            "inserted": inserted_count,
            "updated": updated_count,
            "duplicates_skipped": duplicates_skipped,
            "failed_feeds": failed_feeds,
            "duration_seconds": duration,
            "last_ingested_at": self.last_ingested_at_iso,
        }
        self._last_summary = summary

        # Log according to exact specification
        logger.info(
            "RSS ingestion completed:\n"
            "- feeds_checked: %d\n"
            "- fetched_items: %d\n"
            "- inserted: %d\n"
            "- updated: %d\n"
            "- duplicates_skipped: %d\n"
            "- failed_feeds: %d\n"
            "- duration_seconds: %.2f",
            feeds_checked,
            total_fetched,
            inserted_count,
            updated_count,
            duplicates_skipped,
            failed_feeds,
            duration,
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
            from backend.db.database import SessionLocal, _get_fallback_sessionmaker
            from backend.database.models import Post
            from sqlalchemy import or_

            session = db_session or (SessionLocal() if callable(SessionLocal) else _get_fallback_sessionmaker()())
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
                    session.close()
        except Exception as e:
            logger.warning("[Retention] Cleanup error: %s", e)
            return 0

    def get_stats(self, db_session=None) -> dict[str, Any]:
        """Returns accurate database metrics for total posts, mood breakdown, and category stats."""
        try:
            from backend.db.database import SessionLocal, _get_fallback_sessionmaker
            from backend.database.models import Post
            from sqlalchemy import func

            session = db_session or (SessionLocal() if callable(SessionLocal) else _get_fallback_sessionmaker()())
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
                    session.close()
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
            from backend.db.database import SessionLocal, _get_fallback_sessionmaker
            from backend.database.models import Post

            session = SessionLocal() if callable(SessionLocal) else _get_fallback_sessionmaker()()
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
