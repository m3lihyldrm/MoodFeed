# MoodFeed

## MVP: Kurulum, kapsam ve etik notlar

Bu depo, **çalışan bir FastAPI MVP'si** içerir. MoodFeed; Türkçe sosyal medya akışındaki duygu eğilimi, toksisite ve olumsuz içerik maruziyeti sinyallerini dikkate alan açıklanabilir bir prototiptir.

### MVP'de mevcut

- Yerel JSON dosyasından kurgusal örnek içerik yükleme.
- Duygu/tone, toksisite ve olumsuzluk skorları (0–1).
- Kimliksiz etkileşim skorlarından olumsuz spiral riski hesabı.
- Açık durumdayken açıklanabilir yeniden sıralama; kapalı durumdayken özgün sırayı koruma.
- FastAPI otomatik dokümantasyonu (`/docs`) ve pytest testleri.

### Planlanan veya kapsam dışı

BERTurk eğitimi/entegrasyonu, gerçek kullanıcı testi, A/B testi, kalıcı kullanıcı tercihleri ve üretim performans sonuçları bu MVP'de uygulanmış değildir. Sistem klinik tanı koymaz, kişinin ruhsal durumunu kesin biçimde bildiğini iddia etmez ve gerçek kişisel veri kullanmaz ya da saklamaz.

## Çalıştırma

Python 3.11 ile:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload
```

Servis `http://127.0.0.1:8000`, API dokümantasyonu `http://127.0.0.1:8000/docs` adresindedir.

## API uç noktaları

| Yöntem | Adres | Açıklama |
| --- | --- | --- |
| GET | `/health` | Servis durumunu döndürür. |
| GET | `/feed` | Mevcut ayarla örnek akışı döndürür. |
| POST | `/analyze` | Tek içeriği analiz eder. |
| POST | `/rerank` | İçerikleri ve etkileşimleri sıralar. |
| POST | `/settings/toggle` | Özelliği açar veya kapatır. |
| GET | `/transparency/{content_id}` | Son işlenen içerik için sıralama gerekçesini döndürür. |

Örnek istek:

```bash
curl -X POST http://127.0.0.1:8000/analyze -H "Content-Type: application/json" -d "{\"id\":\"demo-1\",\"text\":\"Bugün güzel bir gün\"}"
```

## Skorlama, şeffaflık ve sınırlılıklar

Varsayılan skorlayıcı; küçük Türkçe olumlu, olumsuz ve saldırgan ifade sözlükleri kullanan deterministik bir yöntemdir, makine öğrenmesi modeli değildir. Skorlar 0–1 aralığına sınırlandırılır. Spiral riski son 10 etkileşim için `0.6 × olumsuzluk kayan ortalaması + 0.4 × olumsuz etkileşim oranı` ile hesaplanır: 0.60 ve üstü yüksek, 0.35–0.59 orta, altı düşük risktir.

Sıralama katsayıları merkezi `ScoreConfig` alanındadır: toksisite cezası 0.35, riskli olumsuzluk cezası 0.25, çeşitlilik bonusu 0.15. Bunlar yalnızca prototip başlangıç değerleridir. `ContentScorer` sözleşmesi gelecekte değerlendirilmiş BERTurk tabanlı bir sağlayıcıyla değiştirilebilir. Sistem içerik silmez; her sıralama kararının gerekçesini döndürür ve kullanıcı istediğinde özelliği kapatabilir.

Yanlış sınıflandırma olasılığı vardır. Sonuçlar yalnızca duygu eğilimi ve olumsuz içerik maruziyeti riski olarak sunulur; otomatik moderasyon veya sağlık değerlendirmesi olarak kullanılmamalıdır. Ayrıntılı veri akışı ve gizlilik yaklaşımı için [mimari belgesine](docs/architecture.md) bakın.

## Testler

```bash
pytest
```

Testler sağlık denetimini, skor sınırlarını, toksisite farkını, spiral riskini, kapalı ayarda özgün sırayı, şeffaflık yanıtını ve geçersiz istekleri doğrular.

Son doğrulama: `python -m pytest -q` komutu geliştirme ortamında **7 test geçti** sonucu verdi.

**Ruh Hâli Duyarlı, Şeffaf ve Etik Sosyal Medya İçerik Akışı**

TEKNOFEST NSosyal İnovasyon Yarışması 2026 — **Sosyal Yapay Zekâ** teması kapsamında geliştirilmektedir.

## Proje Hakkında

MoodFeed, kullanıcının anlık duygu durumunu ve etkileşim örüntüsünü yapay zekâ ile tespit ederek içerik akışını dinamik biçimde yeniden düzenleyen, toksik ve tetikleyici içeriğin akıştaki ağırlığını azaltan ve her karar için gerekçe gösteren bir sistemdir. Amaç kullanıcıyı platformdan uzaklaştırmak değil, aynı süre içinde daha sağlıklı bir içerik dengesi kurmaktır.

## Mimari

Sistem üç katmanlı bir işlem hattı olarak tasarlanmıştır:

1. **Duygu / Ton Analizi** — BERTurk tabanlı ince ayarlı sınıflandırıcı
2. **Toksisite / Moderasyon Skorlaması** — nefret söylemi, taciz ve dezenformasyon riski skorlaması
3. **Akıllı Yeniden Sıralama ve Şeffaflık** — kullanıcıya açıklanabilir sıralama kararları

## Teknoloji Yığını

- **Backend:** Python 3.11, FastAPI
- **Frontend:** React, TypeScript
- **Veritabanı / Önbellek:** PostgreSQL, Redis
- **ML:** PyTorch, HuggingFace Transformers (BERTurk)
- **Altyapı:** Docker, GitHub Actions (CI)

## Klasör Yapısı
