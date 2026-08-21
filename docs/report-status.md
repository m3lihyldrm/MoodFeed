# Teknik rapor durum notu

## Raporda “mevcut” olarak yazılabilecek özellikler

- FastAPI tabanlı MoodFeed MVP.
- Kurgusal JSON demo verisi.
- Varsayılan kural tabanlı Türkçe duygu/tone ve toksisite skoru.
- Opsiyonel hazır fine-tuned BERTurk inference entegrasyonu (`Omar1010/bert-turkish-sentiment`) ve otomatik fallback mekanizması.
- Son etkileşimlerden spiral risk hesabı.
- Açıklanabilir yeniden sıralama ve gerekçe yanıtları.
- MoodFeed açma/kapama seçeneği.
- API endpoint'leri, Swagger dokümantasyonu ve bağımlılıksız tarayıcı demosu.
- Otomatik birim ve entegrasyon testleri.

## Raporda “planlanan” olarak yazılması gereken özellikler

- Kendi veri setimiz üzerinde BERTurk eğitimi / fine-tuning çalışması ve bağımsız değerlendirme.
- Gerçek kullanıcı testi.
- A/B testi.
- Gerçek sosyal medya platformu entegrasyonu.
- Üretim deployment'ı.
- Büyük ölçek performans testi.

## Repo ve doğrulama bilgisi

- Repo: `https://github.com/m3lihyldrm/MoodFeed`
- Çalışma dalı: `add-berturk-inference` (temel dal: `moodfeed-final-prep`)
- Son doğrulanan temel commit: `937209e8cd18bcb210517bffa9dfc9f03327ac19`

## Demo çalıştırma

```bash
python -m pip install -r backend/requirements.txt
uvicorn backend.main:app --reload
```

Tarayıcı demosu `http://127.0.0.1:8000/`, Swagger ise `http://127.0.0.1:8000/docs` adresindedir.

## Raporda kullanılmaması gereken iddialar

- Özel model eğitildi veya kendi veri setimiz üzerinde fine-tune edildi.
- Bağımsız model eğitim metrikleri üretildi.
- Gerçek kullanıcı testi veya A/B testi yapıldı.
- Sistem klinik tanı koyar veya kişinin ruh hâlini kesin bilir.
- Sistem otomatik moderasyon uygular, içerik siler veya hesap kapatır.
- Gerçek sosyal medya platformuna entegredir.
