# MoodFeed MVP

## MoodFeed nedir?

MoodFeed, Türkçe sosyal medya akışlarındaki duygu eğilimi, toksisite sinyalleri ve olumsuz içerik maruziyeti riskini dikkate alarak içeriği açıklanabilir biçimde yeniden sıralayan yerel bir prototiptir. TEKNOFEST NSosyal İnovasyon Yarışması 2026 için hazırlanmıştır.

## Problem

Olumsuz veya saldırgan içeriklerin arka arkaya görülmesi deneyimi zorlaştırabilir. MoodFeed, içeriği silmeden ve kullanıcı hesabı hakkında işlem yapmadan daha dengeli bir akış sırası önermeyi gösterir. Her kararın gerekçesini döndürür; kullanıcı özelliği istediği anda kapatabilir.

## Çözüm

MVP, örnek içerikleri yerel JSON dosyasından alır; kural tabanlı duygu/tone ve toksisite skorları üretir; son etkileşimlerin olumsuzluk sinyalinden spiral riski hesaplar. MoodFeed açıksa içeriği silmeden yeniden sıralar, kapalıysa özgün sırayı korur. Tarayıcı demosu bu sonucu ve Türkçe gerekçeleri görünür kılar.

## MVP kapsamı

### MVP'de gerçekten çalışan özellikler

- Yerel `data/sample_feed.json` dosyasından kurgusal örnek içerik yükleme.
- Deterministik, kural tabanlı Türkçe duygu/tone, toksisite ve olumsuzluk skorlaması.
- Son en fazla 10 kimliksiz etkileşimden olumsuz spiral riski hesaplama.
- Risk ve içerik skorlarıyla açıklanabilir yeniden sıralama.
- MoodFeed kapalıyken özgün sıra ve özgün sıralama puanını koruma.
- FastAPI endpoint'leri, otomatik `/docs` dokümantasyonu, Docker yapılandırması ve testler.
- FastAPI tarafından sunulan, bağımlılıksız HTML/CSS/JavaScript demo arayüzü.

### Planlanan özellikler

- Değerlendirilmiş, yerel BERTurk sağlayıcısı.
- Gerçek kullanıcı araştırması ve A/B testi.
- Kalıcı kullanıcı tercihleri ve üretim ortamı gözlemlenebilirliği.

### Kapsam dışı özellikler

Bu prototip klinik tanı koymaz veya kullanıcının ruhsal durumunu kesin olarak bildiğini iddia etmez. Otomatik moderasyon sistemi değildir; içerik silmez, gizlemez veya kullanıcı hesabı üzerinde işlem yapmaz. Gerçek kişisel veri, API anahtarı ve harici LLM/API kullanılmaz.

## Canlı Dağıtım

### 1. Supabase Kurulumu
1. https://supabase.com → Sign up
2. New Project → MoodFeed
3. Settings → API → URL ve anon key kopyala

### 2. Clerk Kurulumu
1. https://clerk.com → Sign up
2. Create Application → MoodFeed
3. Settings → API Keys → Keys kopyala

### 3. Backend Railway Deploy
1. https://railway.app → New Project
2. Deploy from GitHub → MoodFeed
3. Variables ekle (.env.example'dan)
4. Deploy

### 4. Frontend Vercel Deploy
1. https://vercel.com → Add Project
2. Import Git Repository → MoodFeed
3. Root Directory: frontend
4. Deploy

### 5. Test
- https://moodfeed.vercel.app
- Kayıt ol, email doğrula, giriş yap

## Hızlı Başlangıç & Production Ortamı

MoodFeed, Docker ve PostgreSQL altyapısıyla tek komutla ayağa kaldırılabilir:

```bash
# 1. Ortam değişkenlerini hazırlayın
cp .env.example .env

# 2. Tüm servisleri (FastAPI + PostgreSQL 16 + Redis) Docker ile başlatın
docker compose up -d

# 3. İlk veritabanı migration'ını uygulayın
python -m backend.db.migrations.001_initial_schema

# 4. (Opsiyonel) RSS haber beslemesini senkronize edin
python -m backend.jobs.sync_content
```

- Web Uygulaması & Demo Arayüzü: `http://localhost:8000/`
- Etkileşimli API Dokümantasyonu (Swagger): `http://localhost:8000/docs`
- PostgreSQL Portu: `localhost:5432` (Kullanıcı: `moodfeed`, DB: `moodfeed`)
- Redis Portu: `localhost:6379`

## Kurulum ve Çalıştırma

Python 3.11+ (Python 3.14 dahil) önerilir. Temel çalıştırma için temel bağımlılıklar yeterlidir:

### Temel Kurulum (Kural Tabanlı MVP)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements.txt
uvicorn backend.main:app --reload
```

### Opsiyonel BERTurk ML Bağımlılıkları

BERTurk duygu analizi modelini yerel olarak çalıştırmak için ek ML paketlerini kurabilirsiniz:

```powershell
python -m pip install -r backend/requirements-ml.txt
```

### Scorer Yapılandırması (Environment Variables)

- **Varsayılan Mod (Kural Tabanlı):**
  ```powershell
  $env:MOODFEED_SCORER="rule_based"
  ```
- **BERTurk Modu:**
  ```powershell
  $env:MOODFEED_SCORER="berturk"
  ```
- **Özel Model Belirtme (Opsiyonel):**
  ```powershell
  $env:MOODFEED_BERTURK_MODEL="Omar1010/bert-turkish-sentiment"
  ```

Servis `http://127.0.0.1:8000`, otomatik API dokümantasyonu `http://127.0.0.1:8000/docs` adresinde açılır.

### Docker ile çalıştırma

```bash
docker compose up --build
```

Docker API'yi `http://127.0.0.1:8000` adresinde yayınlar.

## API endpoint'leri

| Yöntem | Adres | Açıklama |
| --- | --- | --- |
| GET | `/health` | Servis durumunu döndürür. |
| GET | `/feed` | Ayara göre örnek akışı analiz edip sıralar. |
| POST | `/analyze` | Tek içeriği analiz eder. |
| POST | `/rerank` | İçerik ve etkileşim listesini sıralar. |
| POST | `/settings/toggle` | MoodFeed'i açar veya kapatır. |
| GET | `/transparency/{content_id}` | Son işlenen içeriğin sıralama gerekçesini döndürür. |
| GET | `/v1/preferences/me` | Kullanıcı tercihlerini getirir (PostgreSQL/SQLAlchemy). |
| POST | `/v1/preferences/me` | Kullanıcı tercihlerini günceller (PostgreSQL/SQLAlchemy). |

### `/analyze` örneği

```bash
curl -X POST http://127.0.0.1:8000/analyze -H "Content-Type: application/json" -d "{\"id\":\"post-001\",\"text\":\"Bugün güzel bir gün\",\"original_score\":0.5}"
```

### `/rerank` örneği

```bash
curl -X POST http://127.0.0.1:8000/rerank -H "Content-Type: application/json" -d "{\"contents\":[{\"id\":\"post-001\",\"text\":\"Bugün güzel bir gün\",\"original_score\":0.5},{\"id\":\"post-002\",\"text\":\"Bu hizmet berbat ve herkes sinirli\",\"original_score\":0.8}],\"interactions\":[{\"negativity_score\":0.9},{\"negativity_score\":0.8}],\"enabled\":true}"
```

Yanıt; `moodfeed_enabled`, `spiral_risk`, içerik analizleri, özgün/yeni sıra, sıralama puanı, Türkçe gerekçeler ve uyarı alanını içerir.

## Demo akışı

Uygulamayı başlattıktan sonra `http://127.0.0.1:8000/` adresini açın. Demo; örnek akışı, aktif analiz/scorer durum rozetini (`⚡ Aktif analiz: Kural Tabanlı`, `🤖 Aktif analiz: BERTurk` veya `⚠️ Aktif analiz: Kural Tabanlı Fallback`), duygu etiketi, toksisite/olumsuzluk skorları ve spiral risk seviyesini gösterir. Toksisite skorunun kural tabanlı hibrit filtreleme ile hesaplandığı arayüzde açıkça belirtilir. Her karttaki **“Neden bu sırada?”** düğmesi açıklamayı açar. Sağ üstteki anahtar MoodFeed'i açıp kapatır; kapalı modda özgün sıra korunur.

## Testler

```bash
python -m compileall backend tests scripts
python -m pytest -v
```

Testler sağlık denetimini, JSON örnek akışını, kural tabanlı ve BERTurk model sözleşmelerini, etiket normalizasyonunu, hata ve fallback mekanizmalarını, sıralama davranışını, API response içindeki scorer metadata alanlarını, PostgreSQL kullanıcı tercihleri kalıcılığını, SUS hesaplamasını, veri dışa aktarım formül enjeksiyonu korumasını ve demo sayfasını doğrular.

## Skorlama yönteminin sınırlılıkları

`RuleBasedTurkishScorer`, küçük bir Türkçe anahtar sözcük sözlüğü kullanan açıklanabilir varsayılan başlangıç yöntemidir. İroni ve bağlamı anlayamaz. `BerturkTurkishScorer` ise opsiyonel olarak hazır eğitilmiş `Omar1010/bert-turkish-sentiment` modelini kullanarak duygu çıkarımı yapar. BERTurk bir toksisite modeli değildir; bu nedenle saldırgan ifade ve toksisite tespiti kural tabanlı sözlük analiziyle hibrit yürütülür. Sistem klinik tanı koymaz veya tedavi iddiası taşımaz; odak noktası dijital yaşam kalitesi ve kullanıcı kontrolüdür.

## Etik ve Gizlilik Yaklaşımı (Privacy by Design)

Örnek veri kurgusaldır. Harici LLM/API veya izleme servisi kullanılmaz. KVKK ve GDPR ilkeleri gözetilerek privacy-by-design yaklaşımı benimsenmiştir; ham gerçek kullanıcı metni veya hassas etkileşim geçmişi kalıcı olarak saklanmaz. Çıktılar yalnızca duygu eğilimi ve olumsuz içerik maruziyeti riski tahminidir. Yanlış sınıflandırma olasılığı vardır; sonuçlar sağlık değerlendirmesi ya da otomatik karar olarak kullanılmamalıdır.

## BERTurk Entegrasyonu, UI Durumu ve Fallback Davranışı

- `ContentScorer` sözleşmesi üzerinden varsayılan kural tabanlı yönteme ek olarak hazır fine-tuned model (`Omar1010/bert-turkish-sentiment`) **deneysel mod** olarak entegre edilmiştir.
- **Varsayılan Karar Verici:** Sistem varsayılan olarak `RuleBasedTurkishScorer` kural tabanlı yöntemini ana karar verici olarak kullanır.
- Web demo arayüzünde (`index.html`) ve API yanıtında (`/feed`, `/rerank`) aktif scorer durumu açıkça raporlanır:
  - **Kural Tabanlı:** `⚡ Aktif analiz: Kural Tabanlı (Varsayılan ve Kararlı)`
  - **Deneysel BERTurk:** `🧪 Aktif analiz: BERTurk (Deneysel Çıkarım - Omar1010/bert-turkish-sentiment)`
  - **Fallback (Yedek Mod):** `⚠️ Aktif analiz: Kural Tabanlı Fallback (BERTurk yüklenemedi; kural tabanlı analiz kullanılıyor)`
- Bu entegrasyon bir çıkarım (inference) sağlayıcısıdır; kendi veri setimiz üzerinde özel fine-tuning eğitimi yapılmamıştır.
- BERTurk bir toksisite modeli olmadığı için toksisite puanı kural tabanlı sözlük filtreleme yöntemiyle hibrit hesaplanır.
- `transformers` veya `torch` kütüphanelerinin eksik olması, modelin indirilememesi ya da çıkarım hatası durumunda sistem 500 hatası üretmez; otomatik olarak `RuleBasedTurkishScorer` analizine fallback yapar, API response'unda ve UI'da fallback durumunu açıkça belirtir.
- Sıralama ve analiz gerekçelerinde kullanılan model kaynağı (`[Kural Tabanlı Skorlama]`, `[Deneysel BERTurk]`, `[Kural Tabanlı Fallback]`) şeffaf biçimde etiketlenir.

## Prototip Değerlendirme Altyapısı (Benchmark)

Kural tabanlı yaklaşım (`RuleBasedTurkishScorer`) ile hazır fine-tuned BERTurk modelinin (`BerturkTurkishScorer`) aynı küçük ve kontrollü sentetik test seti üzerinde karşılaştırılması için prototip değerlendirme altyapısı eklenmiştir.

- **Sentetik Veri Seti:** `data/evaluation_sentiment.csv` (90 satır; 30 pozitif, 30 nötr, 30 negatif sentetik Türkçe cümle, kişisel veri içermez).
- **Değerlendirme Scripti:** `scripts/evaluate_scorers.py`
- **Çıktılar:** `artifacts/evaluation_metrics.json` ve `artifacts/evaluation_errors.csv`
- **Ayrıntılı Dokümantasyon:** [docs/evaluation.md](docs/evaluation.md) ve [data/README.md](data/README.md)

### Değerlendirme Bulguları (90 Sentetik Örnek)
- **Kural Tabanlı (Rule-based):** Accuracy: `0.6889`, Macro F1: `0.6563`
- **BERTurk (Deneysel):** Accuracy: `0.4556`, Macro F1: `0.3898`
- **Mimari Karar:** BERTurk bu sentetik test setinde nötr sınıfına aşırı yönelme eğilimi gösterdiği için ana sıralama kararı kural tabanlı yöntemde tutulmuş, BERTurk yalnızca açıkça seçilen deneysel bir analiz modu olarak konumlandırılmıştır.

### Değerlendirmeyi Çalıştırma
```powershell
python scripts/evaluate_scorers.py
```

### Değerlendirme Sınırlılıkları ve Şeffaflık
- Değerlendirme veri seti kurgusal ve sentetiktir; gerçek bir sosyal medya benchmark'ı veya genel geçer model performans iddiası olarak sunulamaz.
- Depo kapsamında herhangi bir model eğitimi veya fine-tuning yapılmamıştır; `Omar1010/bert-turkish-sentiment` hazır çıkarım modeli olarak kullanılır.
- BERTurk modeli yüklenemediğinde veya bağımlılıklar eksik olduğunda sistem sahte metrik üretmez; BERTurk metrik alanı `null` bırakılır ve hata nedeni açıkça kaydedilir.

## MoodFeed MVP Web Uygulaması Mimarisi (12 Ekran)

Uygulama, bağımlılıksız (Vanilla HTML/CSS/JavaScript) olarak geliştirilmiş, tam responsive ve WCAG 2.2 erişilebilirlik standartlarına uygun modern bir SaaS arayüzüdür:

1. **Karşılama Ekranı (Welcome / Hero):** Sistemin değer önerisi, 3 güven sütunu (şeffaflık, kullanıcı kontrolü, KVKK uyumlu takma adlı depolama).
2. **Başlangıç Rehberi (Onboarding):** 3 adımlı kılavuzlu akış (Algoritma Mantığı, Kontrol Mekanizması, Gizlilik Taahhüdü).
3. **Ana Akış (Main Feed):** 10 zengin sentetik içerik kartı, anlık arama, 5 filtre sekmesi (Tümü, Kaydedilenler, Yeni, Düşük Yoğunluk, Açıklamalı), sıralama seçenekleri (Önerilen, Orijinal, Düşük Tekrar, Yüksek Açıklanabilirlik) ve kart aksiyonları (Kaydet, Paylaş, Detay, Kararı İncele, Geri Al, Sessize Al).
4. **İçerik Detay Görünümü (`#content/<id>`):** Seçilen içeriğin derinlemesine sinyal analizi, duygu polaritesi, toksisite oranı ve doğrudan işlem butonları.
5. **Açıklanabilirlik Çekmecesi (Explanation Drawer):** 4 sütunlu matematiksel formül dökümü ($S_{\text{orig}} - W_{\text{tox}} \cdot T - W_{\text{neg}} \cdot N \cdot R + W_{\text{div}} \cdot D \cdot R$), dikey karar izi ve klavye odak tuzağı (focus trap).
6. **Öngörüler Paneli (Insights Dashboard):** RAM oturumunda işlenen içerik sayıları, kategori dağılım çubuk grafiği ve son etkileşim günlüğü.
7. **Karşılaştırma Ekranı (A/B Compare):** Orijinal ham platform akışı (A) ile MoodFeed önerilen akışını (B) yan yana veya tek kolon görünümünde inceleme.
8. **Akış Tercihleri (Preferences):** 3 sıralama profili (Dengeli, Daha Sakin, Kullanıcı Kontrolü), simüle edilmiş yüksek risk jüri senaryosu toggle'ı ve sessize alınan kaynak yönetimi.
9. **Ayarlar ve Gizlilik (Settings & Privacy):** KVKK ve GDPR uyumlu takma adlı veri politikası (PostgreSQL şifreli), WCAG 2.2 uyumluluk bildirimi ve oturum sıfırlama (reset) onay modalı.
10. **Nasıl Çalışır? / Yardım (Help & FAQ):** Erişilebilir akordeon formatında 6 temel soru-cevap ve etik sınırlar.
11. **Pilot Değerlendirme Modu:** Onam ekranı, 6 adet gerçek UI eylemiyle tamamlanan görev kalitesi takibi (süre, hata, tekrar deneme), 6 soruluk 1–5 Likert anketi, sonuç raporu ve formula-injection korumalı istemci taraflı JSON/CSV dışa aktarma.
12. **404 / Hata Ekranı:** Geçersiz route/hash durumlarında kullanıcıyı ana akışa yönlendiren durum ekranı.

---

## 90 Saniyelik Jüri Demo Senaryosu

1. **00-15 sn (Giriş ve Onboarding):** `http://127.0.0.1:8000/#welcome` açılır. *"🚀 Başlangıç Rehberi"* ile 3 adımlı kılavuz hızlıca gezilir ve *"Akışa Geç"* tıklanır.
2. **15-30 sn (Akış ve Karar İnceleme):** Ana akışta sıralaması değişen bir karta gelinir. *"🔍 Kararı İncele"* tıklanarak 4 sütunlu açıklama çekmecesinde matematiksel formül ve karar izi gösterilir.
3. **30-45 sn (Kullanıcı Kontrolü ve Geri Alma):** Çekmeceden veya karttan *"↩️ Sıralamayı Geri Al"* tıklanır; içeriğin anında orijinal platform sırasına döndüğü ve hiçbir içeriğin silinmediği (`Silinen İçerik: 0`) vurgulanır.
4. **45-60 sn (Tercihler ve Jüri Senaryosu):** *"🎛️ Akış Tercihleri"* sekmesinde *"⚡ Simüle Edilmiş Yüksek Olumsuzluk Senaryosu"* açılır. Yüksek risk ortamında pozitif dengeleyici içeriğin nasıl öne çıktığı gözlemlenir.
5. **60-75 sn (A/B Karşılaştırma):** *"⚖️ Karşılaştır (A/B)"* sekmesine geçilir; Orijinal Platform Sırası (A) ile MoodFeed Önerilen Sırası (B) yan yana kıyaslanır.
6. **75-90 sn (Etik Pilot Değerlendirme & Export):** *"🧪 Pilot Değerlendirme"* başlatılır, onam verilir, görev kalitesi metrikleri (tamamlanma süresi, hata sayısı) ve 1-5 Likert anketi tamamlanıp *"JSON'u İndir"* veya *"CSV'yi İndir"* ile oturum verisi anında dışa aktarılır.

---

## Prototipin raporla ilişkisi

Bu MVP; üç katmanlı karar yaklaşımını (duygu/tone ve toksisite, spiral riski, açıklanabilir sıralama), kullanıcı kontrolünü, veri minimizasyonunu, aktif model şeffaflığını, ölçülebilir değerlendirme altyapısını ve test sürecini somut olarak gösterir. Teknik raporda uygulanmış özellikler yalnızca bu depoda doğrulanabilen bu kapsamla ifade edilmelidir. Ayrıntılar için [mimari belgesine](docs/architecture.md) ve [değerlendirme belgesine](docs/evaluation.md) bakın.

## GitHub dalı ve doğrulama tabanı

Çalışma dalı: `add-evaluation-benchmark` (önceki dallar: `add-scorer-status-ui`, `add-berturk-inference`, temel dal: `moodfeed-final-prep`). Son doğrulanan temel commit `937209e8cd18bcb210517bffa9dfc9f03327ac19` olup teknik rapor durum ayrımı [report-status.md](docs/report-status.md) dosyasında tutulur.
