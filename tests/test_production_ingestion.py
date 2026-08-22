"""Production Content Ingestion & Normalization Tests."""

from backend.ingestion.normalizer import calculate_content_hash, normalize_content_item, normalize_url, strip_html_tags
from backend.ingestion.provider import feed_provider


def test_html_tag_stripping_and_script_removal() -> None:
    raw_html = "<p>Merhaba dünya! <script>alert('xss')</script> Bu bir <b>güvenli</b> içeriktir.</p>"
    clean = strip_html_tags(raw_html)
    assert "alert('xss')" not in clean
    assert "<script>" not in clean
    assert "Merhaba dünya! Bu bir güvenli içeriktir." == clean


def test_content_hash_and_deduplication() -> None:
    h1 = calculate_content_hash("Aynı metin gövdesi.", "Başlık")
    h2 = calculate_content_hash("Aynı metin gövdesi.", "Başlık")
    h3 = calculate_content_hash("Farklı metin gövdesi.", "Başlık")

    assert h1 == h2
    assert h1 != h3


def test_canonical_url_validation() -> None:
    assert normalize_url("https://example.com/haber-1") == "https://example.com/haber-1"
    assert normalize_url("javascript:alert(1)") is None
    assert normalize_url("data:text/html,<script>") is None


def test_rss_xml_parsing() -> None:
    sample_rss = b"""<?xml version="1.0" encoding="UTF-8" ?>
    <rss version="2.0">
      <channel>
        <title>Teknoloji Haberleri</title>
        <item>
          <title>Yapay Zeka ve Seffaflik</title>
          <description>&lt;p&gt;Aciklanabilir yapay zeka modelleri gelisiyor.&lt;/p&gt;</description>
          <link>https://example.com/haber-1</link>
          <author>Ali Veli</author>
        </item>
      </channel>
    </rss>"""

    items = feed_provider.parse_xml_feed(sample_rss)
    assert len(items) == 1
    assert items[0]["title"] == "Yapay Zeka ve Seffaflik"
    assert items[0]["text"] == "Aciklanabilir yapay zeka modelleri gelisiyor."
    assert items[0]["author"] == "Ali Veli"
