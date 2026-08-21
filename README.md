# MoodFeed MVP

## MoodFeed nedir?

MoodFeed, Türkçe sosyal medya akışlarındaki duygu eğilimi, toksisite sinyalleri ve olumsuz içerik maruziyeti riskini dikkate alarak içeriği açıklanabilir biçimde yeniden sıralayan yerel bir prototiptir. TEKNOFEST NSosyal İnovasyon Yarışması 2026 için hazırlanmıştır.

## Problem ve amaç

Olumsuz veya saldırgan içeriklerin arka arkaya görülmesi deneyimi zorlaştırabilir. MoodFeed, içeriği silmeden ve kullanıcı hesabı hakkında işlem yapmadan daha dengeli bir akış sırası önermeyi gösterir. Her kararın gerekçesini döndürür; kullanıcı özelliği istediği anda kapatabilir.

## MVP kapsamı

### MVP'de gerçekten çalışan özellikler

- Yerel `data/sample_feed.json` dosyasından kurgusal örnek içerik yükleme.
- Deterministik, kural tabanlı Türkçe duygu/tone, toksisite ve olumsuzluk skorlaması.
- Son en fazla 10 kimliksiz etkileşimden olumsuz spiral riski hesaplama.
- Risk ve içerik skorlarıyla açıklanabilir yeniden sıralama.
- MoodFeed kapalıyken özgün sıra ve özgün sıralama puanını koruma.
- FastAPI endpoint'leri, otomatik `/docs` dokümantasyonu, Docker yapılandırması ve testler.

### Planlanan özellikler

- Değerlendirilmiş, yerel BERTurk sağlayıcısı.
- Gerçek kullanıcı araştırması ve A/B testi.
- Kalıcı kullanıcı tercihleri ve üretim ortamı gözlemlenebilirliği.

### Kapsam dışı özellikler

Bu prototip klinik tanı koymaz veya kullanıcının ruhsal durumunu kesin olarak bildiğini iddia etmez. Otomatik moderasyon sistemi değildir; içerik silmez, gizlemez veya kullanıcı hesabı üzerinde işlem yapmaz. Gerçek kişisel veri, API anahtarı ve harici LLM/API kullanılmaz.

## Kurulum

Python 3.11 önerilir. Bağımlılıklar yalnızca yerel çalıştırma içindir.

### Windows

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements.txt
uvicorn backend.main:app --reload
```

### Linux/macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.txt
uvicorn backend.main:app --reload
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

## Testler

```bash
python -m compileall backend tests
python -m pytest -q
```

Son doğrulama sonucu: **13 passed**. Testler sağlık denetimini, JSON örnek akışını, skor sınırlarını, toksisite farkını, boş/yüksek spiral riskini, sıralama davranışını, şeffaflık yanıtını, doğrulama hatalarını ve aç/kapat ayarını kapsar.

## Skorlama yönteminin sınırlılıkları

`RuleBasedTurkishScorer`, küçük bir Türkçe anahtar sözcük sözlüğü kullanan açıklanabilir bir başlangıç yöntemidir; gerçek makine öğrenmesi sonucu değildir. İroni, bağlam, lehçe ve çok anlamlı ifadeleri güvenilir biçimde anlayamaz. Tüm skorlar 0–1 aralığına sınırlandırılır. Spiral riski başlangıç eşikleriyle hesaplanır; ölçülmüş kullanıcı davranışı iddiası taşımaz.

## Etik ve KVKK yaklaşımı

Örnek veri kurgusaldır. API anahtarı kullanmaz; ham gerçek kullanıcı metni veya etkileşim geçmişini kalıcı olarak saklamaz. Çıktılar yalnızca duygu eğilimi ve olumsuz içerik maruziyeti riski tahminidir. Yanlış sınıflandırma olasılığı vardır; sonuçlar sağlık değerlendirmesi ya da otomatik karar olarak kullanılmamalıdır.

## BERTurk için sonraki adım ve bilinen eksikler

`ContentScorer` sözleşmesi, mevcut kural tabanlı sağlayıcının ileride BERTurk ile değiştirilmesine imkân verir. Ancak etik veri hazırlama, bağımsız değerlendirme, hata analizi ve yerel model çalışma altyapısı henüz yapılmamıştır. Gerçek kullanıcı testi ve A/B testi de henüz uygulanmamıştır.

## Prototipin raporla ilişkisi

Bu MVP; üç katmanlı karar yaklaşımını (duygu/tone ve toksisite, spiral riski, açıklanabilir sıralama), kullanıcı kontrolünü, veri minimizasyonunu ve test sürecini somut olarak gösterir. Teknik raporda uygulanmış özellikler yalnızca bu depoda doğrulanabilen bu kapsamla ifade edilmelidir. Ayrıntılar için [mimari belgesine](docs/architecture.md) bakın.
