# Teknik rapor durum notu

## Raporda “mevcut” olarak yazılabilecek özellikler

- FastAPI tabanlı MoodFeed MVP.
- Kurgusal JSON demo verisi.
- Kural tabanlı Türkçe duygu/tone ve toksisite skoru.
- Son etkileşimlerden spiral risk hesabı.
- Açıklanabilir yeniden sıralama ve gerekçe yanıtları.
- MoodFeed açma/kapama seçeneği.
- API endpoint'leri, Swagger dokümantasyonu ve bağımlılıksız tarayıcı demosu.
- Otomatik testler.

## Raporda “planlanan” olarak yazılması gereken özellikler

- BERTurk eğitimi veya entegrasyonu.
- Gerçek kullanıcı testi.
- A/B testi.
- Gerçek sosyal medya platformu entegrasyonu.
- Üretim deployment'ı.
- Büyük ölçek performans testi.

## Repo ve doğrulama bilgisi

- Repo: `https://github.com/m3lihyldrm/MoodFeed`
- Çalışma dalı: `moodfeed-final-prep`
- Son doğrulanan temel commit: `937209e8cd18bcb210517bffa9dfc9f03327ac19`
- Final hazırlık test sonucu: `14 passed`

## Demo çalıştırma

```bash
python -m pip install -r backend/requirements.txt
uvicorn backend.main:app --reload
```

Tarayıcı demosu `http://127.0.0.1:8000/`, Swagger ise `http://127.0.0.1:8000/docs` adresindedir.

## Raporda kullanılmaması gereken iddialar

- Gerçek model eğitildi.
- Gerçek kullanıcı testi veya A/B testi yapıldı.
- Sistem klinik tanı koyar veya kişinin ruh hâlini kesin bilir.
- Sistem otomatik moderasyon uygular, içerik siler veya hesap kapatır.
- Gerçek sosyal medya platformuna entegredir.
