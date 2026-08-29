"""Tests for RSS Ingestion Diagnostics, Render Environment Behavior, Structured Logging, and API Endpoints."""

from __future__ import annotations

import datetime
import os
import uuid
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from backend.config import Settings, load_settings_from_env, settings
from backend.database.models import Post, User
from backend.db.database import get_db_session, get_storage_mode, init_db
from backend.main import app
from backend.services.rss_service import RSSService, TURKISH_NEWS_RSS_FEEDS, rss_service


@pytest.fixture(scope="module", autouse=True)
def setup_test_database():
    init_db()


@pytest.fixture
def client():
    return TestClient(app)


# ==============================================================================
# 1. ENVIRONMENT CONFIGURATION TESTS
# ==============================================================================

def test_config_loads_rss_and_debug_env_vars(monkeypatch):
    monkeypatch.setenv("RSS_INGESTION_ENABLED", "false")
    monkeypatch.setenv("RSS_SCHEDULER_ENABLED", "false")
    monkeypatch.setenv("DEBUG_STATUS_ENABLED", "false")
    monkeypatch.setenv("CRON_SECRET", "super-secret-cron-token-12345")
    monkeypatch.setenv("RSS_SYNC_INTERVAL_MINUTES", "5")
    monkeypatch.setenv("RSS_BATCH_LIMIT", "300")
    monkeypatch.setenv("RSS_CUSTOM_FEEDS", "https://custom1.com/rss,https://custom2.com/feed")

    loaded = load_settings_from_env()
    assert loaded.rss_ingestion_enabled is False
    assert loaded.rss_scheduler_enabled is False
    assert loaded.debug_status_enabled is False
    assert loaded.cron_secret == "super-secret-cron-token-12345"
    assert loaded.rss_sync_interval_minutes == 5
    assert loaded.rss_batch_limit == 300
    assert len(loaded.rss_custom_feeds) == 2
    assert "https://custom1.com/rss" in loaded.rss_custom_feeds


def test_config_loads_json_custom_feeds(monkeypatch):
    monkeypatch.setenv("RSS_CUSTOM_FEEDS", '["https://json1.com/rss.xml", "https://json2.com/rss.xml"]')
    loaded = load_settings_from_env()
    assert len(loaded.rss_custom_feeds) == 2
    assert "https://json1.com/rss.xml" in loaded.rss_custom_feeds


# ==============================================================================
# 2. STRUCTURED LOGGING & SUMMARY KEYS TEST
# ==============================================================================

def test_rss_ingestion_structured_log_and_summary_fields(caplog):
    service = RSSService()
    test_guid = str(uuid.uuid4())
    mock_items = [
        {
            "id": f"rss-{test_guid}",
            "title": f"Yapısal Log Test Haberi {test_guid}",
            "text": "Yapısal loglama doğrulaması için metin.",
            "url": f"https://log-test.local/{test_guid}",
            "source": "Log Kaynağı",
            "category": "Gündem",
            "published_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
    ]

    with patch.object(service, "fetch_feed", return_value=mock_items):
        with caplog.at_level("INFO"):
            summary = service.ingest_all_sync()

    required_keys = [
        "configured_feed_count",
        "feeds_checked",
        "feeds_succeeded",
        "feeds_failed",
        "items_fetched",
        "items_normalized",
        "items_inserted",
        "items_updated",
        "duplicates_skipped",
        "storage_mode",
        "elapsed_seconds",
        "errors_summary",
        "last_ingested_at",
    ]
    for key in required_keys:
        assert key in summary, f"Summary missing required key: {key}"

    assert summary["configured_feed_count"] >= 20
    assert summary["items_fetched"] >= 1
    assert summary["storage_mode"] in ("postgresql", "sqlite", "sqlite_fallback")

    # Verify structured log in caplog
    log_text = caplog.text
    assert "configured_feed_count=" in log_text
    assert "feeds_succeeded=" in log_text
    assert "storage_mode=" in log_text
    assert "RSS ingestion summary:" in log_text


# ==============================================================================
# 3. FEED ISOLATION & FAILING FEED RESILIENCE
# ==============================================================================

def test_single_feed_failure_does_not_abort_others():
    service = RSSService()
    call_count = {"success": 0, "fail": 0}

    def mock_fetch(source):
        name = source.get("name", "")
        if "Hata" in name:
            call_count["fail"] += 1
            raise RuntimeError("Simulated network crash for feed")
        call_count["success"] += 1
        item_id = str(uuid.uuid4())
        return [
            {
                "title": f"Özgün Haber {item_id} from {name}",
                "text": f"Özgün içerik açıklaması {item_id}.",
                "url": f"https://example.local/{item_id}",
                "source": name,
                "category": "Gündem",
            }
        ]

    test_sources = [
        {"name": "Kaynak 1", "url": "https://k1.local/rss", "category": "Gündem"},
        {"name": "Hata Kaynak 2", "url": "https://k2.local/rss", "category": "Gündem"},
        {"name": "Kaynak 3", "url": "https://k3.local/rss", "category": "Gündem"},
    ]

    with patch.object(service, "get_configured_feeds", return_value=test_sources):
        with patch.object(service, "fetch_feed", side_effect=mock_fetch):
            summary = service.ingest_all_sync()

    assert summary["feeds_checked"] == 3
    assert summary["feeds_succeeded"] >= 2
    assert summary["items_inserted"] >= 2


# ==============================================================================
# 4. ENCODING, XML/ATOM & HTML HANDLING
# ==============================================================================

def test_parse_rss_xml_with_turkish_encodings():
    service = RSSService()
    # Test ISO-8859-9 / Windows-1254 encoded Turkish text with unescaped &nbsp; and XML entities
    raw_turkish_xml = (
        '<?xml version="1.0" encoding="ISO-8859-9"?>'
        '<rss version="2.0">'
        '<channel>'
        '<title>Türkçe Haber</title>'
        '<item>'
        '<title>İstanbul\'da Büyük Şölen & Coşku &nbsp; Başladı</title>'
        '<description>Açıklama: Sağlık, Eğitim & Çevre yatırımları hız kazandı.</description>'
        '<link>https://haber.tr/istanbul-solen</link>'
        '<pubDate>Thu, 28 Aug 2026 10:00:00 GMT</pubDate>'
        '</item>'
        '</channel>'
        '</rss>'
    ).encode("iso-8859-9")

    items = service.parse_rss_xml(raw_turkish_xml, source_name="Türkçe Test")
    assert len(items) == 1
    assert "İstanbul'da Büyük Şölen" in items[0]["title"]
    assert "Sağlık" in items[0]["text"]


def test_html_response_rejected_gracefully():
    service = RSSService()
    html_landing_page = (
        "<!DOCTYPE html><html lang='tr'><head><title>Haberler</title></head>"
        "<body><h1>Son Dakika</h1><p>Bu bir HTML sayfasıdır, RSS değildir.</p></body></html>"
    )
    items = service.parse_rss_xml(html_landing_page.encode("utf-8"), source_name="HTML Sayfası")
    assert len(items) == 0


def test_atom_feed_parsing():
    service = RSSService()
    atom_xml = """<?xml version="1.0" encoding="utf-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <title>Atom Testi</title>
      <entry>
        <title>Atom Formatında Bilim Haberi</title>
        <link href="https://atom.test/bilim-1"/>
        <summary>Atom özet metni.</summary>
        <updated>2026-08-28T12:00:00Z</updated>
      </entry>
    </feed>
    """
    items = service.parse_rss_xml(atom_xml, source_name="Atom Kaynak")
    assert len(items) == 1
    assert items[0]["title"] == "Atom Formatında Bilim Haberi"
    assert items[0]["url"] == "https://atom.test/bilim-1"


# ==============================================================================
# 5. DATABASE FALLBACK & PERSISTENCE
# ==============================================================================

def test_database_persistence_and_commit():
    session = get_db_session()
    test_url = f"https://persist.test/{uuid.uuid4()}"
    p = Post(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        title="Kalıcı Haber Başlığı",
        content="Kalıcı haber içerik gövdesi.",
        source_name="Kalıcı Kaynak",
        original_url=test_url,
        is_published=True,
    )
    session.add(p)
    session.commit()
    session.close()

    # Read from new session
    session2 = get_db_session()
    try:
        found = session2.query(Post).filter(Post.original_url == test_url).first()
        assert found is not None
        assert found.title == "Kalıcı Haber Başlığı"
    finally:
        session2.close()


# ==============================================================================
# 6. DEBUG STATUS ENDPOINT TESTS
# ==============================================================================

def test_debug_rss_status_endpoint_enabled(client):
    res = client.get("/api/debug/rss-status")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "ingestion_enabled" in data
    assert "scheduler_enabled" in data
    assert "scheduler_running" in data
    assert "source_count" in data
    assert "last_summary" in data
    assert "post_count" in data
    assert "storage_mode" in data
    assert data["source_count"] >= 20
    assert data["post_count"] >= 0


def test_debug_rss_status_disabled_returns_403(client, monkeypatch):
    with patch("backend.config.settings.debug_status_enabled", False):
        res = client.get("/api/debug/rss-status")
        assert res.status_code == 403


# ==============================================================================
# 7. CRON INGEST ENDPOINT TESTS
# ==============================================================================

def test_cron_ingest_manual_trigger_development(client):
    # In development with no secret, should succeed
    with patch.object(rss_service, "ingest_all_sync", return_value={"status": "mock_ok"}):
        res = client.post("/api/cron/ingest")
        assert res.status_code == 200
        assert res.json()["status"] == "ok"


def test_cron_ingest_production_requires_secret(client):
    with patch("backend.config.settings.app_env", "production"):
        with patch("backend.config.settings.cron_secret", "secret-token-xyz"):
            # Missing header -> 401
            res = client.post("/api/cron/ingest")
            assert res.status_code == 401

            # Invalid header -> 401
            res_invalid = client.post("/api/cron/ingest", headers={"Authorization": "Bearer wrong-token"})
            assert res_invalid.status_code == 401

            # Correct header -> 200
            with patch.object(rss_service, "ingest_all_sync", return_value={"status": "prod_ingested"}):
                res_valid = client.post("/api/cron/ingest", headers={"Authorization": "Bearer secret-token-xyz"})
                assert res_valid.status_code == 200


def test_cron_ingest_production_missing_configured_secret(client):
    with patch("backend.config.settings.app_env", "production"):
        with patch("backend.config.settings.cron_secret", None):
            res = client.post("/api/cron/ingest")
            assert res.status_code == 403


# ==============================================================================
# 8. INTEGRATION TEST: HTTP 200 + XML PARSE + DB INSERT CHAIN
# ==============================================================================

def test_integration_xml_parse_and_db_insert_chain(client):
    unique_key = str(uuid.uuid4())
    sample_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
      <channel>
        <title>Entegrasyon Kanalı</title>
        <item>
          <title>Entegrasyon Testi Haberi {unique_key}</title>
          <link>https://entegrasyon.test/{unique_key}</link>
          <description>Entegrasyon testi için haber gövdesi.</description>
          <pubDate>Fri, 28 Aug 2026 12:00:00 GMT</pubDate>
        </item>
      </channel>
    </rss>
    """

    service = RSSService()
    test_source = [{"name": "Entegrasyon Kaynak", "url": f"https://entegrasyon.test/rss-{unique_key}", "category": "Teknoloji"}]

    with patch.object(service, "get_configured_feeds", return_value=test_source):
        with patch.object(service, "fetch_feed") as mock_fetch:
            mock_fetch.return_value = service.parse_rss_xml(
                sample_xml.encode("utf-8"),
                source_name="Entegrasyon Kaynak",
                default_category="Teknoloji",
                source_url=f"https://entegrasyon.test/rss-{unique_key}",
            )
            summary = service.ingest_all_sync()
            assert summary["inserted"] >= 1

    # Verify query via /api/posts
    res = client.get(f"/api/posts?q={unique_key}")
    assert res.status_code == 200
    data = res.json()
    assert data["count"] >= 1
    assert unique_key in data["items"][0]["title"]
    assert data["items"][0]["category"] == "Teknoloji"
