"""MoodFeed Database Seed Script."""
import datetime
import uuid
from backend.database.models import User, Post, Comment, Like, Follow, UserPreferences
from backend.db.database import SessionLocal, init_db, engine

SAMPLE_USERS = [
    {
        "id": uuid.UUID("00000000-0000-0000-0000-000000000001"),
        "email": "demo.kullanici@moodfeed.app",
        "username": "demo_kullanici",
        "display_name": "Demo Kullanıcı",
        "full_name": "Demo Kullanıcı",
        "avatar": "D",
        "bio": "MoodFeed platformu kullanıcısı.",
        "is_verified": True,
    },
    {
        "id": uuid.UUID("00000000-0000-0000-0000-000000000002"),
        "email": "tech.gundem@moodfeed.app",
        "username": "techgundem",
        "display_name": "TechGündem",
        "full_name": "Tech Gündem Haber",
        "avatar": "T",
        "bio": "En güncel teknoloji, yapay zeka ve yazılım haberleri.",
        "is_verified": True,
    },
    {
        "id": uuid.UUID("00000000-0000-0000-0000-000000000003"),
        "email": "kultur.sanat@moodfeed.app",
        "username": "kultursanat",
        "display_name": "KültürSanatRehberi",
        "full_name": "Kültür Sanat Rehberi",
        "avatar": "K",
        "bio": "Kitap, sergi, sinema ve kütüphane incelemeleri.",
        "is_verified": True,
    },
]

SAMPLE_POSTS = [
    {
        "user_id": uuid.UUID("00000000-0000-0000-0000-000000000002"),
        "content": "Bugün düzenlenen teknoloji zirvesinde genç girişimcilerin geliştirdiği projeler büyük ilgi gördü. Gelecek için çok umut verici! #teknoloji #inovasyon",
        "category": "Teknoloji",
        "mood_score": 0.85,
        "mood_label": "happy",
        "sentiment_label": "positive",
        "sentiment_score": 0.95,
        "negativity_score": 0.02,
        "toxicity_score": 0.0,
    },
    {
        "user_id": uuid.UUID("00000000-0000-0000-0000-000000000003"),
        "content": "Kadıköy'de 24 saat açık yeni nesil kütüphane açıldı. Sessiz çalışma salonları ve zengin arşiviyle öğrenciler için harika bir mekan. #kültür #kitap",
        "category": "Kültür",
        "mood_score": 0.75,
        "mood_label": "happy",
        "sentiment_label": "positive",
        "sentiment_score": 0.88,
        "negativity_score": 0.05,
        "toxicity_score": 0.0,
    },
    {
        "user_id": uuid.UUID("00000000-0000-0000-0000-000000000002"),
        "content": "Yol çalışmaları nedeniyle sabah trafiğinde uzun kuyruklar oluştu. Sürücülere alternatif güzergahları kullanmaları tavsiye ediliyor. #trafik",
        "category": "Gündem",
        "mood_score": -0.65,
        "mood_label": "sad",
        "sentiment_label": "negative",
        "sentiment_score": 0.82,
        "negativity_score": 0.78,
        "toxicity_score": 0.20,
    },
    {
        "user_id": uuid.UUID("00000000-0000-0000-0000-000000000001"),
        "content": "Toplu taşıma ücretlerine yapılan fahiş zamlar vatandaşları çileden çıkardı, herkes tepkili! #zam #ulaşım",
        "category": "Ekonomi",
        "mood_score": -0.80,
        "mood_label": "angry",
        "sentiment_label": "negative",
        "sentiment_score": 0.92,
        "negativity_score": 0.85,
        "toxicity_score": 0.45,
    },
    {
        "user_id": uuid.UUID("00000000-0000-0000-0000-000000000001"),
        "content": "Hafta sonu beklenen fırtına ve aşırı yağışlar sebebiyle sel uyarısı yapıldı, endişeli bekleyiş sürüyor. #hava",
        "category": "Gündem",
        "mood_score": -0.45,
        "mood_label": "anxious",
        "sentiment_label": "negative",
        "sentiment_score": 0.70,
        "negativity_score": 0.60,
        "toxicity_score": 0.05,
    },
]

def seed_database():
    init_db(engine)
    db = SessionLocal()
    try:
        for u_data in SAMPLE_USERS:
            existing = db.query(User).filter(User.id == u_data["id"]).first()
            if not existing:
                u = User(**u_data)
                db.add(u)
        db.commit()

        for p_data in SAMPLE_POSTS:
            existing = db.query(Post).filter(Post.content == p_data["content"]).first()
            if not existing:
                post = Post(
                    id=uuid.uuid4(),
                    user_id=p_data["user_id"],
                    content=p_data["content"],
                    title=p_data["content"][:40] + "...",
                    category=p_data["category"],
                    mood_score=p_data["mood_score"],
                    mood_label=p_data["mood_label"],
                    sentiment_label=p_data["sentiment_label"],
                    sentiment_score=p_data["sentiment_score"],
                    negativity_score=p_data["negativity_score"],
                    toxicity_score=p_data["toxicity_score"],
                    language="tr",
                    is_published=True,
                )
                db.add(post)
        db.commit()
        print("✓ Database seeded successfully.")
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
