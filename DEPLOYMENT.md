# MoodFeed Dağıtım ve Çalıştırma Kılavuzu (Production Runbook)

Bu belge, MoodFeed uygulamasının **Local (Geliştirme)**, **Render (FastAPI Backend)** ve **Vercel (Frontend SPA)** ortamlarında eşitlik içinde, kararlı ve güvenli biçimde çalıştırılması için gerekli yapılandırma adımlarını içerir.

---

## 1. Sistem ve Dağıtım Mimarisi

MoodFeed, ayrık ve yüksek performanslı 2 ana dağıtım katmanından oluşur:

```
┌────────────────────────────────────────────────────────┐
│                   VERCEL (Frontend)                    │
│             https://mood-feed-two.vercel.app           │
│   • Modern SPA (Vite / Vanilla JS / CSS Design System) │
│   • VITE_API_BASE_URL ile doğrudan Render API'ye erişir│
└───────────────────────────┬────────────────────────────┘
                            │ HTTPS / REST / JSON
                            ▼
┌────────────────────────────────────────────────────────┐
│                    RENDER (Backend)                    │
│          https://<your-service>.onrender.com           │
│   • FastAPI & Uvicorn (Python 3.11+)                   │
│   • Lifespan & Non-blocking Async Background RSS Task  │
│   • Kural Tabanlı Duygu Analizi & Mood Sıralama        │
│   • CORS İzinli: https://mood-feed-two.vercel.app      │
└───────────────────────────┬────────────────────────────┘
                            │ SQLAlchemy 2.0 (Pool Pre-ping)
                            ▼
┌────────────────────────────────────────────────────────┐
│                 VERİTABANI (Persistence)               │
│   • Production: PostgreSQL 16 (Render/Neon/Supabase)   │
│   • Local Dev: SQLite (moodfeed_local.db) Fallback     │
│   • 90 Günlük Otomatik RSS Arşiv Saklama               │
└────────────────────────────────────────────────────────┘
```

---

## 2. Render Deployment Runbook (FastAPI Backend)

### Dashboard Ayarları
- **Service Type:** Web Service
- **Environment:** Python 3
- **Branch:** `main`
- **Root Directory:** `backend`
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `python -m uvicorn main:app --host 0.0.0.0 --port $PORT`
- **Health Check Path:** `/health`
- **Auto-Deploy:** Yes

### Environment Variables Tablosu (Render Dashboard)

| Değişken Adı | Örnek / Değer | Açıklama |
| --- | --- | --- |
| `APP_ENV` | `production` | Production modunu aktifleştirir. |
| `PORT` | `10000` | Render tarafından otomatik atanır. |
| `CORS_ORIGINS` | `https://mood-feed-two.vercel.app,http://localhost:8000,http://127.0.0.1:8000` | Frontend kökenlerine izin verir. |
| `DATABASE_URL` | `postgresql+psycopg2://user:pass@host:5432/dbname` | Kalıcı PostgreSQL bağlantısı (`postgres://` otomatik dönüştürülür). |
| `SESSION_SECRET` | *(32+ karakter rastgele dize)* | Oturum güvenliği için zorunlu üretim anahtarı. |
| `JWT_SECRET` | *(32+ karakter rastgele dize)* | JWT token imzalama anahtarı. |
| `EXPORT_SIGNING_SECRET` | *(32+ karakter rastgele dize)* | Veri dışa aktarım imzalama anahtarı. |
| `RSS_INGESTION_ENABLED` | `true` | Arka plan RSS çekim servisini çalıştırır. |
| `DATA_RETENTION_DAYS` | `90` | Eski RSS verilerinin saklanma süresi (gün). |

### Render Smoke Test Adımları
Render deploy'u tamamlandıktan sonra aşağıdaki uç noktaları test edin:

```bash
# 1. Health Liveness (HTTP 200)
curl -i https://<render-service>.onrender.com/health
# Yanıt: {"status":"ok","service":"moodfeed-api","environment":"production","version":"1.0.0"}

# 2. OpenAPI Şeması (HTTP 200)
curl -i https://<render-service>.onrender.com/openapi.json

# 3. Swagger UI Dokümantasyonu (HTTP 200)
curl -i https://<render-service>.onrender.com/docs

# 4. Haberler ve Sayfalama (HTTP 200)
curl -i "https://<render-service>.onrender.com/api/posts?limit=5&offset=0"

# 5. İstatistikler & 6 Mood Dağılımı (HTTP 200)
curl -i https://<render-service>.onrender.com/api/posts/stats

# 6. MoodFeed Feed Sıralama (HTTP 200)
curl -i https://<render-service>.onrender.com/api/feed
```

---

## 3. Vercel Deployment Runbook (Frontend UI)

### Dashboard Ayarları
- **Framework Preset:** Vite (veya Other)
- **Root Directory:** `frontend`
- **Build Command:** `npm run build`
- **Output Directory:** `dist`
- **Branch:** `main`

### Environment Variables Tablosu (Vercel Dashboard)

| Değişken Adı | Değer | Açıklama |
| --- | --- | --- |
| `VITE_API_BASE_URL` | `https://<your-render-service>.onrender.com` | Render'da koşan FastAPI backend public URL'i. |

### Vercel Smoke Test Adımları
1. `https://mood-feed-two.vercel.app` adresini tarayıcıda açın.
2. Tarayıcı Geliştirici Araçları (DevTools) -> **Network** sekmesini açın.
3. `/api/posts` ve `/api/posts/stats` isteklerinin başarıyla HTTP 200 döndüğünü ve feed kartlarının gerçek RSS verisiyle render edildiğini doğrulayın.
4. Mood filtre butonlarına (Sakin, Neşeli, Kaygılı, Üzgün, Kızgın) tıklayarak filtrelemenin anında çalıştığını teyit edin.
5. "Daha Fazla Göster" butonuna tıklayarak sayfalama (pagination) isteğinin yeni içerikleri getirdiğini doğrulayın.

---

## 4. Free-Tier ve Veritabanı Kısıtları

- **Render Free Web Service Uyku Modu (Cold Start):**
  Render Free katmanı 15 dakika hareketsiz kaldığında servisi uykuya alır. İlk istek geldiğinde sunucunun uyanması 30-50 saniye sürebilir. Frontend'de bu durum algılanır, iskelet yükleyici (skeleton) ve "Render backend servisi uyanıyor" bilgilendirmesi ile kullanıcıya güvenli deneyim sunulur.

- **Kalıcı Veri & SQLite vs PostgreSQL:**
  Render Free instance'lar geçici (ephemeral) dosya sistemine sahiptir. Sunucu yeniden başladığında yerel SQLite dosyası sıfırlanabilir. Üretim ortamında RSS arşivinin ve kullanıcı tercihlerinin kalıcı olarak birikmesi için harici bir PostgreSQL (Render Postgres, Neon, Supabase) `DATABASE_URL` olarak tanımlanmalıdır.

---

## 5. Yerel Geliştirme (Local Dev)

Yerel geliştirme ortamında tek komutla hem backend hem frontend çalıştırılabilir:

```powershell
# 1. Sanal ortamı etkinleştirin ve gereksinimleri kurun
python -m pip install -r backend/requirements.txt

# 2. Uvicorn sunucusunu başlatın
cd backend
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

- Yerel Arayüz: `http://127.0.0.1:8000/`
- Yerel API Dokümantasyonu: `http://127.0.0.1:8000/docs`
- Yerel Health Kontrolü: `http://127.0.0.1:8000/health`
