"""Tests for RSS Ingestion & Synchronization."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest

from backend.ingestion.rss_feed import RSSFeedParser, rss_parser
from backend.ingestion.normalizer import strip_html_tags, calculate_content_hash
from backend.jobs.sync_content import ContentSyncJob


SAMPLE_RSS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Haberler Gündem</title>
    <link>https://www.haberler.com</link>
    <description>Son Dakika Haberler</description>
    <item>
      <title>Yapay Zeka ve Geleceğin Teknolojileri Zirvesi</title>
      <link>https://www.haberler.com/teknoloji/yapay-zeka-zirvesi-12345/</link>
      <description><![CDATA[<p>İstanbul'da düzenlenen <b>büyük teknoloji zirvesi</b> yoğun katılımla gerçekleşti.</p>]]></description>
      <author>Teknoloji Masası</author>
      <category>Teknoloji</category>
      <pubDate>Thu, 27 Aug 2026 12:00:00 GMT</pubDate>
      <guid>https://www.haberler.com/teknoloji/yapay-zeka-zirvesi-12345/</guid>
    </item>
    <item>
      <title>Halk Kütüphanesi Yenilenen Binasında Hizmete Açıldı</title>
      <link>https://www.haberler.com/kultur/kutuphane-acildi-67890/</link>
      <description>Şehir kütüphanesi modern çalışma alanlarıyla gençlerin hizmetine sunuldu.</description>
      <author>Kültür Servisi</author>
      <category>Kültür</category>
      <pubDate>Thu, 27 Aug 2026 11:30:00 GMT</pubDate>
      <guid>https://www.haberler.com/kultur/kutuphane-acildi-67890/</guid>
    </item>
  </channel>
</rss>
"""

SAMPLE_ATOM_XML = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Atom Feed Örneği</title>
  <link href="https://example.com/feed"/>
  <updated>2026-08-27T12:00:00Z</updated>
  <entry>
    <title>Genç Girişimcilerden Yenilikçi Projeler</title>
    <link href="https://example.com/entry/1"/>
    <id>urn:uuid:1225c695-cfb8-4ebb-aaaa-80da344efa6a</id>
    <updated>2026-08-27T12:00:00Z</updated>
    <summary>Girişimcilik yarışmasında çevre dostu projeler ödüllendirildi.</summary>
    <author>
      <name>Girişim Haber</name>
    </author>
    <category term="Girişimcilik"/>
  </entry>
</feed>
"""


def test_strip_html_tags_and_hashing() -> None:
    html_raw = "<div><p>Merhaba <strong>Dünya</strong>! <script>alert(1);</script></p></div>"
    cleaned = strip_html_tags(html_raw)
    assert cleaned == "Merhaba Dünya !"
    assert "<script>" not in cleaned

    hash1 = calculate_content_hash("İçerik metni", "Başlık")
    hash2 = calculate_content_hash("İçerik metni", "Başlık")
    assert hash1 == hash2
    assert len(hash1) == 64


def test_rss_xml_parsing() -> None:
    parser = RSSFeedParser()
    items = parser.parse_xml(SAMPLE_RSS_XML)
    assert len(items) == 2

    item1 = items[0]
    assert item1["title"] == "Yapay Zeka ve Geleceğin Teknolojileri Zirvesi"
    assert "büyük teknoloji zirvesi" in item1["text"]
    assert "<p>" not in item1["text"]
    assert item1["category"] == "Teknoloji"
    assert item1["source"] == "rss"

    item2 = items[1]
    assert item2["title"] == "Halk Kütüphanesi Yenilenen Binasında Hizmete Açıldı"
    assert item2["category"] == "Kültür"


def test_atom_xml_parsing() -> None:
    parser = RSSFeedParser()
    items = parser.parse_xml(SAMPLE_ATOM_XML)
    assert len(items) == 1

    entry = items[0]
    assert entry["title"] == "Genç Girişimcilerden Yenilikçi Projeler"
    assert "çevre dostu projeler" in entry["text"]
    assert entry["author"] == "Girişim Haber"
    assert entry["category"] == "Girişimcilik"
    assert entry["source"] == "atom"


@patch("requests.get")
def test_fetch_feed_mocked(mock_get: MagicMock) -> None:
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = SAMPLE_RSS_XML.encode("utf-8")
    mock_get.return_value = mock_resp

    items = rss_parser.fetch_feed("https://mock.haber.com/rss")
    assert len(items) == 2
    assert items[0]["title"] == "Yapay Zeka ve Geleceğin Teknolojileri Zirvesi"


@patch("backend.ingestion.rss_feed.rss_parser.fetch_feed")
def test_content_sync_job(mock_fetch: MagicMock) -> None:
    mock_fetch.return_value = [
        {
            "guid": "rss-test-guid-1",
            "title": "Bilim ve İnovasyon",
            "text": "Geliştirilen yeni batarya teknolojisi temiz enerji depolamada devrim yaratıyor.",
            "author": "Bilim Masası",
            "category": "Teknoloji",
            "published_at": "2026-08-27T12:00:00Z",
            "content_hash": "hash123456",
            "source": "rss",
        }
    ]

    job = ContentSyncJob()
    result = job.sync_feed(feed_url="https://mock.haber.com/rss", limit=5)
    assert result["synced_count"] >= 1
    assert len(result["posts"]) >= 1
    post = result["posts"][0]
    assert post["title"] == "Bilim ve İnovasyon"
    assert "sentiment_label" in post
    assert "negativity_score" in post
    assert "toxicity_score" in post
