"""Tests for Turkish RSS Aggregation Service."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest

from fastapi.testclient import TestClient
from backend.services.rss_service import RSSService, rss_service, TURKISH_NEWS_RSS_FEEDS
from backend.main import app, load_live_feed, load_feed_contents

client = TestClient(app)


SAMPLE_BBC_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>BBC News Türkçe</title>
    <link>https://www.bbc.com/turkce</link>
    <description>BBC Türkçe Güncel Haberler</description>
    <item>
      <title>Türkiye ve Dünya Ekonomisinde Son Gelişmeler</title>
      <description><![CDATA[Piyasalarda <b>enflasyon ve büyüme</b> verileri yakından takip ediliyor.]]></description>
      <link>https://www.bbc.com/turkce/articles/c123456</link>
      <pubDate>Thu, 27 Aug 2026 14:00:00 GMT</pubDate>
      <guid>https://www.bbc.com/turkce/articles/c123456</guid>
    </item>
    <item>
      <title>Yenilenebilir Enerjide Tarihi Rekor</title>
      <description>Güneş ve rüzgar enerjisi üretimi küresel ölçekte yeni bir rekora ulaştı.</description>
      <link>https://www.bbc.com/turkce/articles/c789012</link>
      <pubDate>Thu, 27 Aug 2026 13:30:00 GMT</pubDate>
      <guid>https://www.bbc.com/turkce/articles/c789012</guid>
    </item>
  </channel>
</rss>
"""

SAMPLE_DW_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>DW Türkçe</title>
    <link>https://www.dw.com/tr</link>
    <item>
      <title>Bilim İnsanları Yeni Bir Gezegen Keşfetti</title>
      <description>James Webb Teleskobu yaşama elverişli atmosferik koşullara sahip yeni bir ötegezegen tespit etti.</description>
      <link>https://www.dw.com/tr/bilim-yeni-gezegen/a-987654</link>
      <pubDate>Thu, 27 Aug 2026 12:45:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""


def test_rss_service_sources_configured() -> None:
    assert len(TURKISH_NEWS_RSS_FEEDS) >= 3
    names = [f["name"] for f in TURKISH_NEWS_RSS_FEEDS]
    assert "BBC Türkçe" in names
    assert any("DW" in n for n in names)
    assert any("TRT" in n for n in names)


def test_parse_rss_xml_extracts_fields() -> None:
    service = RSSService()
    items = service.parse_rss_xml(SAMPLE_BBC_XML.encode("utf-8"), source_name="BBC Türkçe", default_category="Ekonomi")

    assert len(items) == 2
    item1 = items[0]
    assert item1["title"] == "Türkiye ve Dünya Ekonomisinde Son Gelişmeler"
    assert "enflasyon ve büyüme" in item1["text"]
    assert "<b>" not in item1["text"]  # HTML tags stripped
    assert item1["url"] == "https://www.bbc.com/turkce/articles/c123456"
    assert item1["source"] == "BBC Türkçe"
    assert "2026-08-27" in item1["published_at"]
    assert item1["id"].startswith("rss-")


def test_rss_service_handles_corrupt_xml_gracefully() -> None:
    service = RSSService()
    items = service.parse_rss_xml(b"<not valid xml", source_name="Bozuk XML")
    assert items == []


def test_rss_service_fetch_feed_error_returns_empty_list() -> None:
    service = RSSService(timeout_seconds=1)
    items = service.fetch_feed({"name": "Test", "url": "https://invalid-non-existent-domain-12345.com/rss.xml"})
    assert isinstance(items, list)
    assert len(items) == 0


@patch.object(RSSService, "fetch_feed")
def test_fetch_all_feeds_interleaves_and_caches(mock_fetch_feed: MagicMock) -> None:
    service = RSSService(cache_ttl_seconds=60)
    parsed_sample = service.parse_rss_xml(SAMPLE_BBC_XML.encode("utf-8"), source_name="BBC Türkçe", default_category="Gündem")
    mock_fetch_feed.return_value = parsed_sample

    items = service.fetch_all_feeds(force_refresh=True)

    assert len(items) >= 2
    assert items[0]["source"] == "BBC Türkçe"

    inputs = service.get_live_content_inputs(limit=5)
    assert len(inputs) >= 2
    assert len(inputs[0].title) > 0
    assert inputs[0].url.startswith("http")
    assert len(inputs[0].source) > 0


@patch("backend.services.rss_service.rss_service.get_live_content_inputs")
def test_live_feed_endpoint_with_source_live(mock_get_live: MagicMock) -> None:
    from backend.models import ContentInput
    mock_get_live.return_value = [
        ContentInput(
            id="live-1",
            text="Canlı Türkçe haber metni özeti.",
            title="Canlı Haber Başlığı",
            url="https://haber.local/1",
            source="TRT Haber",
            published_at="27.08.2026",
            original_score=0.75,
        )
    ]

    res = client.get("/feed?source=live")
    assert res.status_code == 200
    body = res.json()
    assert len(body["contents"]) >= 1
    item = body["contents"][0]
    assert item["title"] == "Canlı Haber Başlığı"
    assert item["source"] == "TRT Haber"
    assert item["url"] == "https://haber.local/1"
