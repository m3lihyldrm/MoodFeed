# MoodFeed Dağıtım ve Çalıştırma Kılavuzu (Deployment Guide)

Bu belge, MoodFeed projesinin yerel geliştirme, Docker konteyner ortamı ve üretim/demo sunucu ortamlarında dağıtımı için gerekli mimari bileşenleri, ortam değişkenlerini ve doğrulama adımlarını açıklar.

---

## 1. Sistem Mimarisi

MoodFeed 3 katmanlı, hafif ve yüksek performanslı bir mimariye sahiptir:

1. **Frontend Katmanı (Statik HTML/CSS/JS):**
   - Bağımsız, hafif Vanilla JavaScript, CSS custom properties (Editorial Calm Intelligence tasarım sistemi) ve anlamsal HTML5.
   - Doğrudan FastAPI `FileResponse` üzerinden veya NGINX / statik dosya sunucusuyla sunulur.
   - İstemci tarafında `MoodFeedApiAdapter` ile REST API'ye bağlanır.

2. **Backend API Katmanı (FastAPI / Uvicorn / Python 3.11+):**
   - Asenkron ve tip güvenli REST API uç noktaları (`/feed`, `/rerank`, `/analyze`, `/v1/preferences/me`, vb.).
   - Modüler kural tabanlı skorlayıcı (`RuleBasedTurkishScorer`) ve opsiyonel BERTurk çıkarım sağlayıcısı (`BerturkTurkishScorer`).
   - SUS (System Usability Scale) hesaplama motoru ve formül enjeksiyonuna karşı korumalı CSV/JSON export altyapısı.

3. **Veritabanı Katmanı (PostgreSQL 16 & SQLAlchemy):**
   - PostgreSQL 16 ilişkisel veritabanı.
   - `users`, `user_preferences` (JSONB destekli kaynak sessize alma) ve `interaction_logs` tabloları.
   - SQLAlchemy 2.0 ORM katmanı ile tip güvenli oturum ve veri yönetimi.

```
[ Tarayıcı / İstemci (HTML/CSS/JS) ]
                 │
                 ▼ HTTP / JSON
[ FastAPI Backend (Uvicorn / Python 3.14) ]
   ├── Scoring & Reranking Engine (Rule-based / BERTurk fallback)
   ├── Explanation & Decision Trace Service
   └── Preferences Service (SQLAlchemy 2.0)
                 │
                 ▼ PostgreSQL Wire Protocol
[ PostgreSQL 16 Veritabanı (moodfeed) ]
   ├── users
   ├── user_preferences (JSONB)
   └── interaction_logs (JSONB)
```

---

## 2. Ortam Değişkenleri (Environment Variables)

`.env.example` dosyasından türetilen yapılandırma parametreleri:

| Değişken | Varsayılan Değer | Açıklama |
| --- | --- | --- |
| `APP_ENV` | `development` | Çalışma ortamı (`development`, `staging`, `production`). |
| `APP_NAME` | `MoodFeed` | Uygulama adı. |
| `HOST` | `0.0.0.0` | Dinlenecek ağ adresi. |
| `PORT` | `8000` | Dinlenecek port numarası. |
| `DATABASE_URL` | `postgresql://moodfeed:moodfeed@localhost:5432/moodfeed` | PostgreSQL bağlantı URL'i. |
| `DATABASE_POOL_SIZE` | `10` | SQLAlchemy bağlantı havuzu boyutu. |
| `DATABASE_MAX_OVERFLOW` | `20` | Havuz aşım bağlantı limiti. |
| `MOODFEED_SCORER` | `rule_based` | Aktif skorlayıcı modu (`rule_based`, `berturk`). |
| `MODEL_PROVIDER` | `rule_based` | ML sağlayıcı seçimi. |
| `LOG_LEVEL` | `INFO` | Günlükleme seviyesi (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |
| `LOG_FORMAT` | `json` | Günlükleme formatı (`json`, `text`). |

---

## 3. Dağıtım Adımları

### A. Docker Compose ile Hızlı Dağıtım (Önerilen)

```bash
# Servisleri derleyip arka planda çalıştırın
docker compose up -d --build

# Veritabanı sağlık kontrolünü doğrulayın
docker compose ps
```

Erişim:
- Arayüz: `http://localhost:8000/`
- API Dokümantasyonu: `http://localhost:8000/docs`

### B. Yerel Geliştirme Ortamında Manuel Başlatma

```bash
# 1. PostgreSQL veritabanını Docker ile ayağa kaldırın
docker compose up -d db

# 2. Şemayı veritabanına uygulayın
psql "$DATABASE_URL" -f backend/db/schema.sql

# 3. Python sanal ortamını hazırlayın ve paketleri kurun
python -m venv .venv
# Windows:
.venv\Scripts\Activate.ps1
# Linux/macOS:
# source .venv/bin/activate

python -m pip install -r backend/requirements.txt

# 4. Sunucuyu başlatın
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 4. Test ve Doğrulama Komutları

Tüm sistem bileşenlerinin, modellerin ve uç noktaların hatasız çalıştığını doğrulamak için:

```bash
# 1. Kod tabanının derleme denetimi (0 hata beklenir)
python -m compileall backend tests scripts

# 2. Tam test paketini çalıştırın
python -m pytest -v
```

---

## 5. Güvenlik ve Gizlilik Prensipleri (Privacy by Design)

- **Sıfır Kalıcı İstemci Depolaması:** Tarayıcı tarafında `localStorage` veya izleme çerezi kullanılmaz; demo oturum durumu RAM belleğinde işlenir.
- **CSV Formül Enjeksiyonu Koruması:** Dışa aktarılan dosyalarda `=`, `+`, `-`, `@`, `\t`, `\r` karakterleriyle başlayan hücreler `'` ile sanitize edilir (OWASP ASVS uyumlu).
- **Açıklanabilirlik:** Sıralama kararları matematiksel formül ve dikey karar iziyle şeffaf şekilde kullanıcıya sunulur.
- **Kullanıcı Kontrolü:** Kullanıcı istediği an sıralamayı geri alabilir (`revert`), kaynakları sessize alabilir veya MoodFeed filtresini devre dışı bırakabilir.
