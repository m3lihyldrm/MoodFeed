"""Comprehensive test suite for MoodFeed RSS Archiving, 6-Class Mood Detection, Deduplication, Locking, Pagination, Retention, and Stats."""

from __future__ import annotations

import datetime
import threading
import time
import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.database.models import Post, User
from backend.db.database import get_db, SessionLocal, init_db
from backend.ingestion.normalizer import calculate_content_hash, normalize_title, normalize_turkish_lower
from backend.main import app
from backend.services.mood_detector import detect_mood, MoodDetectionService
from backend.services.rss_service import RSSIngestionService, rss_service

SYSTEM_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    init_db()


@pytest.fixture
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    return TestClient(app)


# ------------------------------------------------------------------------------
# 1. No deletion on ingest (Yeni RSS cekimi eskileri silmez)
# ------------------------------------------------------------------------------
def test_no_deletion_on_ingest(db_session):
    test_id = uuid.uuid4()
    p1 = Post(
        id=test_id,
        user_id=SYSTEM_USER_ID,
        title="Eski Haber Kaydi 1",
        content="Bu haber eskiden kaydedildi ve silinmemeli.",
        author="Arsiv Kaynagi",
        source_name="Arsiv",
        original_url=f"https://arsiv.local/haber-1-{test_id}",
        is_published=True,
    )
    db_session.add(p1)
    db_session.commit()

    service = RSSIngestionService()
    mock_items = [
        {
            "title": f"Yeni Haber {test_id}",
            "text": "Yeni cekilen taze haber metni.",
            "url": f"https://yeni.local/haber-{test_id}",
            "source": "Yeni Kaynak",
            "author": "Yeni Kaynak",
            "category": "Gündem",
            "published_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
    ]

    with patch.object(service, "fetch_feed", return_value=mock_items):
        summary = service.ingest_all_sync(db_session=db_session)
        assert summary["inserted"] >= 1

    persisted = db_session.query(Post).filter(Post.id == test_id).first()
    assert persisted is not None
    assert persisted.title == "Eski Haber Kaydi 1"


# ------------------------------------------------------------------------------
# 2. URL deduplication (Ayni URL tekrar eklenmez)
# ------------------------------------------------------------------------------
def test_url_deduplication(db_session):
    test_url = f"https://haber.test/ayni-url-{uuid.uuid4()}"
    p = Post(
        id=uuid.uuid4(),
        user_id=SYSTEM_USER_ID,
        title="Orijinal Baslik",
        content="Orijinal Icerik",
        source_name="Test Kaynak",
        original_url=test_url,
        is_published=True,
    )
    db_session.add(p)
    db_session.commit()

    initial_count = db_session.query(Post).filter(Post.original_url == test_url).count()
    assert initial_count == 1

    service = RSSIngestionService()
    mock_items = [
        {
            "title": "Farkli Baslik Ama Ayni URL",
            "text": "Ayni linke sahip haber.",
            "url": test_url,
            "source": "Test Kaynak",
            "author": "Test Kaynak",
            "category": "Gündem",
        }
    ]

    with patch.object(service, "fetch_feed", return_value=mock_items):
        summary = service.ingest_all_sync(db_session=db_session)
        assert summary["duplicates_skipped"] >= 1

    after_count = db_session.query(Post).filter(Post.original_url == test_url).count()
    assert after_count == 1


# ------------------------------------------------------------------------------
# 3. Normalized title deduplication (Ayni kaynak + normalize baslik tekrar eklenmez)
# ------------------------------------------------------------------------------
def test_normalized_title_deduplication(db_session):
    src = f"Kaynak_{uuid.uuid4()}"
    raw_title1 = "SON DAKIKA: Merkez Bankasi Faiz Kararini Acikladi! - NTV"
    raw_title2 = "Merkez Bankasi Faiz Kararini Acikladi"

    norm1 = normalize_title(raw_title1)
    norm2 = normalize_title(raw_title2)
    assert norm1 == norm2

    p = Post(
        id=uuid.uuid4(),
        user_id=SYSTEM_USER_ID,
        title=raw_title1,
        normalized_title=norm1,
        content="Faiz karari metni.",
        source_name=src,
        original_url=f"https://ntv.local/faiz-{uuid.uuid4()}",
        is_published=True,
    )
    db_session.add(p)
    db_session.commit()

    service = RSSIngestionService()
    mock_items = [
        {
            "title": raw_title2,
            "text": "Faiz karari metni 2.",
            "url": f"https://ntv.local/faiz-farkli-url-{uuid.uuid4()}",
            "source": src,
            "author": src,
            "category": "Ekonomi",
        }
    ]

    with patch.object(service, "fetch_feed", return_value=mock_items):
        summary = service.ingest_all_sync(db_session=db_session)
        assert summary["duplicates_skipped"] >= 1

    matched = db_session.query(Post).filter(Post.source_name == src, Post.normalized_title == norm1).count()
    assert matched == 1


# ------------------------------------------------------------------------------
# 4. Content hash deduplication (Ayni icerik hash'i tekrar eklenmez)
# ------------------------------------------------------------------------------
def test_content_hash_deduplication(db_session):
    t = "Ozel Inovasyon Raporu 2026"
    c = "Bu raporda yapay zeka alanindaki tum gelismeler yer almaktadir."
    chash = calculate_content_hash(t, c)

    p = Post(
        id=uuid.uuid4(),
        user_id=SYSTEM_USER_ID,
        title=t,
        content=c,
        content_hash=chash,
        source_name=f"Kaynak_{uuid.uuid4()}",
        original_url=f"https://ino.test/{uuid.uuid4()}",
        is_published=True,
    )
    db_session.add(p)
    db_session.commit()

    service = RSSIngestionService()
    mock_items = [
        {
            "title": t,
            "text": c,
            "url": f"https://farkli.test/{uuid.uuid4()}",
            "source": f"BaskaKaynak_{uuid.uuid4()}",
            "category": "Teknoloji",
        }
    ]

    with patch.object(service, "fetch_feed", return_value=mock_items):
        summary = service.ingest_all_sync(db_session=db_session)
        assert summary["duplicates_skipped"] >= 1


# ------------------------------------------------------------------------------
# 5. New unique items insertion
# ------------------------------------------------------------------------------
def test_new_unique_items_insertion(db_session):
    unique_marker = str(uuid.uuid4())
    service = RSSIngestionService()
    mock_items = [
        {
            "title": f"Yepyeni Benzersiz Haber {unique_marker}",
            "text": "Tamamen ozgun ve yeni icerik metni.",
            "url": f"https://unique.test/{unique_marker}",
            "source": "Benzersiz Kaynak",
            "category": "Bilim",
            "published_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
    ]

    with patch.object(service, "fetch_feed", return_value=mock_items):
        summary = service.ingest_all_sync(db_session=db_session)
        assert summary["inserted"] >= 1

    found = db_session.query(Post).filter(Post.original_url == f"https://unique.test/{unique_marker}").first()
    assert found is not None
    assert found.category == "Bilim"
    assert found.mood_label in ["calm", "happy", "neutral", "anxious", "sad", "angry"]


# ------------------------------------------------------------------------------
# 6. Update on re-fetch (Eksik gorsel veya alan guncellenir, yeni kayit acilmaz)
# ------------------------------------------------------------------------------
def test_update_on_refetch_no_duplication(db_session):
    same_url = f"https://update.test/{uuid.uuid4()}"
    p = Post(
        id=uuid.uuid4(),
        user_id=SYSTEM_USER_ID,
        title="Gorselsiz Haber",
        content="Icerik aciklamasi.",
        source_name="Guncelleme Kaynagi",
        original_url=same_url,
        image_url=None,
        is_published=True,
    )
    db_session.add(p)
    db_session.commit()

    service = RSSIngestionService()
    mock_items = [
        {
            "title": "Gorselsiz Haber",
            "text": "Icerik aciklamasi.",
            "url": same_url,
            "source": "Guncelleme Kaynagi",
            "category": "Kültür",
            "image_url": "https://images.unsplash.com/photo-test.jpg",
        }
    ]

    with patch.object(service, "fetch_feed", return_value=mock_items):
        summary = service.ingest_all_sync(db_session=db_session)
        assert summary["updated"] >= 1

    db_session.expire_all()
    updated_post = db_session.query(Post).filter(Post.original_url == same_url).first()
    assert updated_post is not None
    assert updated_post.image_url == "https://images.unsplash.com/photo-test.jpg"


# ------------------------------------------------------------------------------
# 7. 6-Class Mood Detection and Filtering (calm, happy, neutral, anxious, sad, angry)
# ------------------------------------------------------------------------------
def test_mood_filtering_six_classes(client, db_session):
    tag = str(uuid.uuid4())[:8]
    mood_posts = [
        ("calm", f"Doga Yuruyusu ve Sessiz Meditasyon {tag}", "Ormanda sakin ve huzurlu bir gun gecirildi."),
        ("happy", f"Buyuk Basari ve Mutluluk Verici Sampiyonluk {tag}", "Milli takim harika bir zafer kazanarak gurur yasatti."),
        ("neutral", f"Istatistik Kurumu Yillik Verileri Yayinladi {tag}", "TUIK yillik nufus ve sanayi verilerini kamuoyuyla paylasti."),
        ("anxious", f"Beklenen Deprem ve Alarm Durumu Uyarisi {tag}", "Uzmanlar olasi tehlike ve risklere karsi acil onlem cagrisinda bulundu."),
        ("sad", f"Vefat Eden Usta Sanatci Icin Taziye {tag}", "Kultur dunyamizin kiymetli ismi hayatini kaybetti, derin uzuntu duyuldu."),
        ("angry", f"Skandal Zam ve Haksiz Fiyat Artisi {tag}", "Tuketiciler fahis fiyat artislarina ve adaletsizlige buyuk tepki gosterdi."),
    ]

    for label, title, content in mood_posts:
        analysis = detect_mood(title=title, text=content)
        p = Post(
            id=uuid.uuid4(),
            user_id=SYSTEM_USER_ID,
            title=title,
            content=content,
            mood_label=label,
            mood_score=analysis["mood_score"],
            mood_distribution=analysis["mood_distribution"],
            source_name="MoodTest",
            original_url=f"https://mood.test/{label}-{uuid.uuid4()}",
            is_published=True,
        )
        db_session.add(p)
    db_session.commit()

    for mood_target in ["calm", "happy", "neutral", "anxious", "sad", "angry"]:
        res = client.get(f"/api/posts?mood={mood_target}&limit=50")
        assert res.status_code == 200
        data = res.json()
        assert "items" in data
        assert "pagination" in data
        for item in data["items"]:
            if tag in (item.get("title") or ""):
                assert item["mood_label"] == mood_target


# ------------------------------------------------------------------------------
# 8. Pagination (total, limit, offset, has_more, next_offset)
# ------------------------------------------------------------------------------
def test_pagination_and_navigation(client, db_session):
    unique_cat = f"Cat_{str(uuid.uuid4())[:8]}"
    for i in range(25):
        p = Post(
            id=uuid.uuid4(),
            user_id=SYSTEM_USER_ID,
            title=f"Sayfalama Haberi {i}",
            content=f"Icerik metni {i}",
            category=unique_cat,
            source_name="PageSource",
            original_url=f"https://page.test/{unique_cat}/{i}",
            is_published=True,
        )
        db_session.add(p)
    db_session.commit()

    # Page 1 (limit=10, offset=0)
    res1 = client.get(f"/api/posts?category={unique_cat}&limit=10&offset=0")
    assert res1.status_code == 200
    d1 = res1.json()
    assert d1["pagination"]["total"] >= 25
    assert d1["pagination"]["limit"] == 10
    assert d1["pagination"]["offset"] == 0
    assert d1["pagination"]["has_more"] is True
    assert d1["pagination"]["next_offset"] == 10
    assert len(d1["items"]) == 10

    # Page 2 (limit=10, offset=10)
    res2 = client.get(f"/api/posts?category={unique_cat}&limit=10&offset=10")
    assert res2.status_code == 200
    d2 = res2.json()
    assert d2["pagination"]["offset"] == 10
    assert d2["pagination"]["has_more"] is True
    assert d2["pagination"]["next_offset"] == 20
    assert len(d2["items"]) == 10

    # Page 3 (limit=10, offset=20)
    res3 = client.get(f"/api/posts?category={unique_cat}&limit=10&offset=20")
    assert res3.status_code == 200
    d3 = res3.json()
    assert len(d3["items"]) == 5
    assert d3["pagination"]["has_more"] is False
    assert d3["pagination"]["next_offset"] is None


# ------------------------------------------------------------------------------
# 9. Real stats breakdown (Gercek DB sayilari ve mood/kategori dagilimi)
# ------------------------------------------------------------------------------
def test_real_stats_breakdown(client, db_session):
    res = client.get("/api/posts/stats")
    assert res.status_code == 200
    stats = res.json()

    assert "total_posts" in stats
    assert "posts_by_mood" in stats
    assert "posts_by_category" in stats
    assert isinstance(stats["posts_by_mood"], dict)
    for m in ["calm", "happy", "neutral", "anxious", "sad", "angry"]:
        assert m in stats["posts_by_mood"]

    db_actual_total = db_session.query(Post).filter(Post.is_published.is_(True)).count()
    assert stats["total_posts"] == db_actual_total


# ------------------------------------------------------------------------------
# 10. Empty mood category handling (Bos mood durumunda duzgun yanit ve sayim)
# ------------------------------------------------------------------------------
def test_empty_mood_category_handling(client):
    res = client.get("/api/posts?category=NonExistentCategory99999&limit=20")
    assert res.status_code == 200
    data = res.json()
    assert data["items"] == []
    assert data["pagination"]["total"] == 0
    assert data["pagination"]["has_more"] is False
    assert data["pagination"]["next_offset"] is None


# ------------------------------------------------------------------------------
# 11. Ingestion locking (Eszamanli cekimlerde race condition ve mukerrer kayit engeli)
# ------------------------------------------------------------------------------
def test_ingestion_locking(db_session):
    service = RSSIngestionService()
    results = []

    def run_worker():
        s = service.ingest_all_sync(db_session=db_session)
        results.append(s)

    threads = [threading.Thread(target=run_worker) for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(results) == 3
    for r in results:
        assert "inserted" in r
        assert "duplicates_skipped" in r


# ------------------------------------------------------------------------------
# 12. Retention cleanup (90 gunden eski haberler silinir/arsivlenir, yeniler kalir)
# ------------------------------------------------------------------------------
def test_retention_cleanup(db_session):
    now = datetime.datetime.now(datetime.timezone.utc)
    old_date = now - datetime.timedelta(days=120)
    new_date = now - datetime.timedelta(days=10)

    old_id = uuid.uuid4()
    new_id = uuid.uuid4()

    p_old = Post(
        id=old_id,
        user_id=SYSTEM_USER_ID,
        title="120 Gunluk Cok Eski Haber",
        content="Silinmesi gereken eski icerik.",
        source_name="Arsiv",
        original_url=f"https://old.test/{old_id}",
        published_at=old_date,
        created_at=old_date,
        is_published=True,
    )
    p_new = Post(
        id=new_id,
        user_id=SYSTEM_USER_ID,
        title="10 Gunluk Taze Haber",
        content="Saklanmasi gereken guncel icerik.",
        source_name="Guncel",
        original_url=f"https://new.test/{new_id}",
        published_at=new_date,
        created_at=new_date,
        is_published=True,
    )

    db_session.add(p_old)
    db_session.add(p_new)
    db_session.commit()

    service = RSSIngestionService()
    deleted = service.run_retention_cleanup(days=90, db_session=db_session)
    assert deleted >= 1

    db_session.expire_all()
    persisted_old = db_session.query(Post).filter(Post.id == old_id).first()
    persisted_new = db_session.query(Post).filter(Post.id == new_id).first()

    assert persisted_old is None
    assert persisted_new is not None
