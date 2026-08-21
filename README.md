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

## Kurulum ve Çalıştırma

Python 3.11 önerilir. Temel çalıştırma için temel bağımlılıklar yeterlidir:

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

Uygulamayı başlattıktan sonra `http://127.0.0.1:8000/` adresini açın. Demo; örnek akışı, duygu etiketi, toksisite/olumsuzluk skorları ve spiral risk seviyesini gösterir. Her karttaki **“Neden bu sırada?”** düğmesi açıklamayı açar. Sağ üstteki anahtar MoodFeed'i açıp kapatır; kapalı modda özgün sıra korunur.

## Testler

```bash
python -m compileall backend tests
python -m pytest -q
```

Testler sağlık denetimini, JSON örnek akışını, kural tabanlı ve BERTurk model sözleşmelerini, etiket normalizasyonunu, hata ve fallback mekanizmalarını, sıralama davranışını ve demo sayfasını doğrular.

## Skorlama yönteminin sınırlılıkları

`RuleBasedTurkishScorer`, küçük bir Türkçe anahtar sözcük sözlüğü kullanan açıklanabilir bir başlangıç yöntemidir. İroni ve bağlamı anlayamaz. `BerturkTurkishScorer` ise hazır eğitilmiş `Omar1010/bert-turkish-sentiment` modelini kullanarak duygu çıkarımı yapar. BERTurk bir toksisite modeli olmadığı için saldırgan ifade tespiti kural tabanlı sözlük analiziyle hibrit yürütülür. Sistem klinik değerlendirme veya kesin ruhsal durum tespiti iddiası taşımaz.

## Etik ve KVKK yaklaşımı

Örnek veri kurgusaldır. API anahtarı kullanmaz; ham gerçek kullanıcı metni veya etkileşim geçmişini kalıcı olarak saklamaz. Çıktılar yalnızca duygu eğilimi ve olumsuz içerik maruziyeti riski tahminidir. Yanlış sınıflandırma olasılığı vardır; sonuçlar sağlık değerlendirmesi ya da otomatik karar olarak kullanılmamalıdır.

## BERTurk Entegrasyonu ve Fallback Davranışı

- `ContentScorer` sözleşmesi üzerinden hazır fine-tuned model (`Omar1010/bert-turkish-sentiment`) entegre edilmiştir.
- Bu entegrasyon bir inference sağlayıcısıdır; kendi veri setimiz üzerinde özel fine-tuning eğitimi veya metrik üretimi yapılmamıştır.
- `transformers` veya `torch` kütüphanelerinin eksik olması, modelin indirilememesi ya da çıkarım hatası durumunda sistem 500 hatası üretmez; otomatik olarak `RuleBasedTurkishScorer` kural tabanlı analizine fallback yapar ve bu durumu gerekçe listesinde açıkça belirtir.
- Gerçek kullanıcı testi ve A/B testi henüz uygulanmamıştır.

## Prototipin raporla ilişkisi

Bu MVP; üç katmanlı karar yaklaşımını (duygu/tone ve toksisite, spiral riski, açıklanabilir sıralama), kullanıcı kontrolünü, veri minimizasyonunu ve test sürecini somut olarak gösterir. Teknik raporda uygulanmış özellikler yalnızca bu depoda doğrulanabilen bu kapsamla ifade edilmelidir. Ayrıntılar için [mimari belgesine](docs/architecture.md) bakın.

## GitHub dalı ve doğrulama tabanı

Çalışma dalı: `add-berturk-inference` (temel dal: `moodfeed-final-prep`). Son doğrulanan temel commit `937209e8cd18bcb210517bffa9dfc9f03327ac19` olup teknik rapor durum ayrımı [report-status.md](docs/report-status.md) dosyasında tutulur.
