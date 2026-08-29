"""Tests for RSS News Ingestion Optimization & Real-Time Stats."""

from __future__ import annotations

import unittest.mock as mock
from fastapi.testclient import TestClient
from apscheduler.triggers.interval import IntervalTrigger

from backend.main import app, scheduler
from backend.services.rss_service import (
    RSSService,
    rss_service,
    RSS_FEEDS,
    TURKISH_NEWS_RSS_FEEDS,
    RSSIngestionService,
)
from backend.config import RSS_FEEDS as CONFIG_RSS_FEEDS

client = TestClient(app)


def test_rss_feeds_configuration_at_least_20_sources() -> None:
    """Verify that at least 20+ RSS feeds are configured in config and rss_service."""
    assert len(RSS_FEEDS) >= 20
    assert len(CONFIG_RSS_FEEDS) >= 20
    assert len(TURKISH_NEWS_RSS_FEEDS) >= 20

    # Verify key Turkish media outlets exist
    all_urls = " ".join(RSS_FEEDS)
    assert "trthaber.com" in all_urls
    assert "ntv.com.tr" in all_urls
    assert "haberturk.com" in all_urls
    assert "sozcu.com.tr" in all_urls
    assert "milliyet.com.tr" in all_urls
    assert "bbc.com" in all_urls
    assert "dw.com" in all_urls
    assert "euronews.com" in all_urls
    assert "webtekno.com" in all_urls
    assert "shiftdelete.net" in all_urls
    assert "donanimhaber.com" in all_urls


def test_scheduler_configured_for_one_minute_interval() -> None:
    """Verify AsyncIOScheduler has rss_ingestion job scheduled every 1 minute."""
    job = scheduler.get_job("rss_ingestion")
    assert job is not None
    assert isinstance(job.trigger, IntervalTrigger)
    # 1 minute = 60 seconds interval
    assert job.trigger.interval.total_seconds() == 60


def test_deduplication_filters_identical_title_and_link() -> None:
    """Verify RSS deduplication cleans duplicate news articles."""
    service = RSSService()
    feed_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
      <channel>
        <title>Haber Kanalı</title>
        <item>
          <title>Aynı Haber Başlığı</title>
          <link>https://haber.com/haber-1</link>
          <description>Haber metni açıklaması.</description>
          <pubDate>Fri, 28 Aug 2026 12:00:00 GMT</pubDate>
        </item>
        <item>
          <title>Aynı Haber Başlığı</title>
          <link>https://haber.com/haber-1</link>
          <description>Farklı bir açıklama ama aynı başlık ve link.</description>
          <pubDate>Fri, 28 Aug 2026 12:05:00 GMT</pubDate>
        </item>
        <item>
          <title>Farklı Haber Başlığı</title>
          <link>https://haber.com/haber-2</link>
          <description>İkinci haber açıklaması.</description>
          <pubDate>Fri, 28 Aug 2026 12:10:00 GMT</pubDate>
        </item>
      </channel>
    </rss>
    """

    with mock.patch("urllib.request.urlopen") as mock_urlopen:
        mock_resp = mock.MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = feed_xml.encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        items = service.fetch_all_feeds(force_refresh=True)
        # Should deduplicate down to 2 distinct items
        titles = [i["title"] for i in items if i["title"] in ("Aynı Haber Başlığı", "Farklı Haber Başlığı")]
        assert len(titles) == 2


def test_api_posts_stats_endpoint() -> None:
    """Verify /api/posts/stats endpoint returns total_posts, today_posts, and last_updated."""
    res = client.get("/api/posts/stats")
    assert res.status_code == 200
    data = res.json()
    assert "total_posts" in data
    assert "today_posts" in data
    assert "last_updated" in data
    assert isinstance(data["total_posts"], int)
    assert isinstance(data["today_posts"], int)
    assert data["total_posts"] >= 0

    # Also test /v1/posts/stats
    res_v1 = client.get("/v1/posts/stats")
    assert res_v1.status_code == 200
    assert res_v1.json()["total_posts"] == data["total_posts"]


def test_rss_ingestion_service_alias() -> None:
    """Verify RSSIngestionService alias exists and provides ingest_all."""
    svc = RSSIngestionService()
    assert hasattr(svc, "ingest_all")
    assert hasattr(svc, "fetch_all_feeds")
