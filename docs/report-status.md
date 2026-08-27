# Teknik rapor durum notu

## Raporda “mevcut” olarak yazılabilecek özellikler

- FastAPI tabanlı MoodFeed MVP.
- Kurgusal JSON demo verisi.
- Varsayılan ve kararlı ana karar verici olarak `RuleBasedTurkishScorer` Türkçe duygu/tone ve toksisite skoru.
- Açıkça seçilen opsiyonel deneysel BERTurk çıkarım modu (`Omar1010/bert-turkish-sentiment`, `is_experimental=True`) ve otomatik şeffaf fallback mekanizması (`rule_based_fallback`).
- Son etkileşimlerden spiral risk hesabı.
- Açıklanabilir yeniden sıralama, model şeffaflık etiketleri (`[Kural Tabanlı Skorlama]`, `[Deneysel BERTurk]`, `[Kural Tabanlı Fallback]`) ve gerekçe yanıtları.
- Akış Kontrol Merkezi (`balanced`, `calmer`, `user_control` kullanıcı profil ağırlıkları).
- Jüri Demosu için simüle edilmiş yüksek olumsuzluk senaryosu (`scenario=high_negativity`, $R \approx 0.91$) ve şeffaf sentetik etiketleme.
- Sağdan kayan Explainability Drawer ve adım adım matematiksel skor formülü dökümü (`score_breakdown`: ham skor, toksisite cezası, negatiflik cezası, çeşitlilik bonusu, nihai skor).
- Demo Studio modu (hızlı jüri preset'leri, tek tıkla demo sıfırlama, 3 adımlı "Nasıl Çalışır?" mimari paneli).
- Bireysel içerik sıralama geri alma ("Sıralamayı Geri Al" / "Öneriyi Uygula", sıfır içerik silme garantisi).
- Etik ve anonim "Pilot Kullanıcı Değerlendirmesi" modu (açık onam ekranı, 6 adımlı gerçek görev takip paneli, 1-5 Likert anketi, maruziyet sinyal raporu; hiçbir kalıcı depolama veya kişisel veri kullanılmaz).
- Bellek içi "Görev Kalitesi" ve süre analitiği (her görev için `duration_ms`, `error_count`, `retry_count`, durum takibi, form doğrulama odaklama yönetimi; sahte veri veya kalıcı depolama içermez).
- İstemci taraflı (memory-only) anonim pilot oturumu JSON ve CSV dışa aktarma (export) özelliği (sunucusuz Blob indirme, CSV enjeksiyon koruması, şeffaflık ve etik metadata üstbilgileri).
- MoodFeed açma/kapama seçeneği.
- API endpoint'leri, Swagger dokümantasyonu ve bağımlılıksız tarayıcı demosu.
- Dengeli sentetik test veri seti (`data/evaluation_sentiment.csv`, 90 satır) ve modüler prototip değerlendirme altyapısı (`scripts/evaluate_scorers.py`).
- Sentetik kontrol seti değerlendirme sonuçları: Kural tabanlı Accuracy: 0.6889, Macro F1: 0.6563; Deneysel BERTurk Accuracy: 0.4556, Macro F1: 0.3898.
- BERTurk model yükleme hatasında sahte metrik üretmeyip `null` bırakan şeffaf hata koruma ve artifact çıktısı (`artifacts/evaluation_metrics.json`, `artifacts/evaluation_errors.csv`).
- Otomatik birim ve entegrasyon testleri.

## Raporda “planlanan” olarak yazılması gereken özellikler

- Kendi veri setimiz üzerinde BERTurk eğitimi / fine-tuning çalışması ve bağımsız geniş ölçekli değerlendirme.
- Gerçek kullanıcı testi.
- A/B testi.
- Gerçek sosyal medya platformu entegrasyonu.
- Üretim deployment'ı.
- Büyük ölçek performans testi.

## Repo ve doğrulama bilgisi

- Repo: `https://github.com/m3lihyldrm/MoodFeed`
- Çalışma dalı: `add-evaluation-benchmark` (önceki dallar: `add-scorer-status-ui`, `add-berturk-inference`, temel dal: `moodfeed-final-prep`)
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
- 90 örnekli sentetik test setinin genel geçer büyük sosyal medya benchmark'ı olduğu iddiası.
- Script çalıştırılmadan farazi metrik iddiası.
- Gerçek kullanıcı testi veya A/B testi yapıldı.
- Sistem klinik tanı koyar veya kişinin ruh hâlini kesin bilir.
- Sistem otomatik moderasyon uygular, içerik siler veya hesap kapatır.
- Gerçek sosyal medya platformuna entegredir.
