# MoodFeed Veri Setleri Dokümantasyonu

Bu dizinde MoodFeed prototipinde kullanılan yerel ve sentetik veri dosyaları yer almaktadır.

---

## 1. `sample_feed.json`
- **Amaç:** Web arayüzü ve API demosu için kullanılan kurgusal sosyal medya akış örnekleri.
- **İçerik:** Kurgusal kullanıcı metinleri, ilk sıralama puanları (`original_score`).
- **Gizlilik:** Tamamen sentetiktir, kişisel veri içermez.

---

## 2. `evaluation_sentiment.csv`
- **Amaç:** `RuleBasedTurkishScorer` ile hazır fine-tuned `BerturkTurkishScorer` sağlayıcılarının aynı küçük ve dengeli kontrol seti üzerinde kıyaslanması.
- **Boyut:** Toplam 90 satır (30 `positive`, 30 `neutral`, 30 `negative`).
- **Biçim:** `text,label`
- **Karakteristik:** Kısa ve sentetik Türkçe cümleler.

### ⚠️ Önemli Sınırlılıklar ve Etik Bildirim
1. **Sentetik Veri:** Bu veri seti kurgusal olarak üretilmiştir. Gerçek sosyal medya mesajları, kullanıcı adları, kişisel veri veya özel iletişim verisi içermez.
2. **Benchmark Niteliği:** Bu dosya genel geçer bir akademik sosyal medya benchmark'ı değildir. Yalnızca prototip seviyesinde tutarlılık, model yükleme kontrolü ve kural tabanlı/transformer karşılaştırması için oluşturulmuş küçük bir doğrulama setidir.
3. **Genellenebilirlik:** Bu 90 örnek üzerinde elde edilen metrikler modellerin gerçek dünya genelleme performansını tek başına temsil etmez.
