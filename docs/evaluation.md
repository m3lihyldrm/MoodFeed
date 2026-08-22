# MoodFeed Değerlendirme ve Benchmark Altyapısı

Bu dokümantasyon, MoodFeed prototipinde kullanılan duygu analizi skorlayıcılarının (`RuleBasedTurkishScorer` ve `BerturkTurkishScorer`) ölçülebilir biçimde değerlendirilmesi ve karşılaştırılması için geliştirilen altyapıyı açıklar.

---

## 1. Amaç ve Kapsam

MoodFeed mimarisinde duygu analizi katmanı için iki farklı yaklaşım desteklenir:
1. **RuleBasedTurkishScorer:** Harici bağımlılık gerektirmeyen, deterministik anahtar kelime eşleşmesiyle çalışan açıklanabilir kural tabanlı skorlayıcı.
2. **BerturkTurkishScorer:** Hugging Face üzerinde açık olarak paylaşılan hazır fine-tuned `Omar1010/bert-turkish-sentiment` modelini kullanan derin öğrenme tabanlı çıkarım sağlayıcısı.

Değerlendirme altyapısının amacı; bu iki yaklaşımı aynı küçük, dengeli ve kontrollü test seti üzerinde çalıştırarak aralarındaki farkları, hata örüntülerini ve model yükleme davranışını somut olarak gözlemlemektir.

---

## 2. Değerlendirme Veri Seti (`data/evaluation_sentiment.csv`)

- **Örnek Sayısı:** Toplam 90 satır.
- **Sınıf Dağılımı:**
  - 30 `positive` (olumlu)
  - 30 `neutral` (nötr)
  - 30 `negative` (olumsuz)
- **Sütun Yapısı:** `text,label`
- **Dil:** Türkçe.

### ⚠️ Veri Setinin Sınırlılıkları ve Etik Bildirim
- **Tamamen Sentetik:** Veri setindeki tüm cümleler kurgusal olarak üretilmiştir. Gerçek sosyal medya mesajı, kullanıcı adı, kişisel veri (KVKK) veya özel iletişim içeriği içermez.
- **Genel Benchmark Değildir:** Bu 90 örnek, genel geçer büyük ölçekli bir Türkçe duygu analizi benchmark'ı niteliğinde değildir. Yalnızca prototip seviyesinde regresyon testi, model yükleme kontrolü ve kural tabanlı/transformer karşılaştırması için küçük bir kontrol setidir.
- **Eğitim Verisi Değildir:** Depo kapsamında herhangi bir model eğitimi veya fine-tuning işlemi yapılmamıştır.

---

## 3. Değerlendirme Scripti (`scripts/evaluate_scorers.py`)

Değerlendirme aracı saf Python ile yazılmış olup temel metrikler için ek harici kütüphane zorunluluğu taşımaz.

### Çalıştırma

Temel ortamda çalıştırmak için:
```powershell
python scripts/evaluate_scorers.py
```

Opsiyonel değerlendirme araçlarını (`scikit-learn`, `pandas`) kurmak için:
```powershell
python -m pip install -r backend/requirements-evaluation.txt
```

### Script İşleyişi
1. `data/evaluation_sentiment.csv` dosyasını okur ve sütun/etiket doğrulaması yapar.
2. Sınıf dağılımını konsola yazdırır.
3. Metinleri `RuleBasedTurkishScorer` ile analiz eder, metrikleri hesaplar ve hataları toplar.
4. Metinleri `BerturkTurkishScorer` ile analiz etmeyi dener:
   - **Model Başarıyla Yüklendiyse:** İnference sonuçlarını değerlendirir, metrikleri hesaplar ve hataları listeler.
   - **Model Yüklenemediyse / Fallback Durumundaysa:** Asla sahte metrik veya fallback sonuçlarını BERTurk metriği gibi üretmez; konsola hata gerekçesini yazar ve BERTurk metrik alanını `null` olarak kaydeder.
5. Sonuçları `artifacts/` dizini altına iki dosya olarak kaydeder:
   - `artifacts/evaluation_metrics.json`
   - `artifacts/evaluation_errors.csv`

---

## 4. Çıktı Dosyaları ve Formatlar

### A. Metrikler Dosyası (`artifacts/evaluation_metrics.json`)

```json
{
  "evaluation_timestamp": "2026-08-21T14:30:00.000000+00:00",
  "dataset_type": "synthetic",
  "dataset_warning": "Bu veri seti kurgusal ve sentetik bir test setidir; gerçek sosyal medya benchmark'ı veya genel geçer model performans iddiası değildir.",
  "sample_count": 90,
  "class_distribution": {
    "negative": 30,
    "neutral": 30,
    "positive": 30
  },
  "metrics": {
    "rule_based": {
      "accuracy": 0.xxxx,
      "macro_precision": 0.xxxx,
      "macro_recall": 0.xxxx,
      "macro_f1": 0.xxxx,
      "confusion_matrix": [
        [..., ..., ...],
        [..., ..., ...],
        [..., ..., ...]
      ],
      "class_metrics": { ... }
    },
    "berturk": null
  },
  "errors_file": "artifacts/evaluation_errors.csv",
  "berturk_status": {
    "loaded": false,
    "reason": "Transformers/PyTorch kütüphaneleri bulunamadı."
  }
}
```

*Not: Confusion matrix sınıfları `[negative, neutral, positive]` sırasındadır.*

### B. Hata Dökümü (`artifacts/evaluation_errors.csv`)

| content_id | text | true_label | predicted_label | scorer |
| --- | --- | --- | --- | --- |
| `eval-rule-031` | Saat 14.00'te toplantı odasında buluşacağız. | `neutral` | `neutral` | `rule_based` |

---

## 5. Sentetik Kontrol Seti Değerlendirme Sonuçları

`scripts/evaluate_scorers.py` scripti `data/evaluation_sentiment.csv` sentetik veri seti üzerinde fiilen çalıştırılmış ve aşağıdaki sonuçlar elde edilmiştir:

| Metrik | RuleBasedTurkishScorer (Varsayılan) | BerturkTurkishScorer (Deneysel) |
| --- | --- | --- |
| **Accuracy (Doğruluk)** | **0.6889** (%68.89) | **0.4556** (%45.56) |
| **Macro Precision** | 0.8114 | 0.7932 |
| **Macro Recall** | 0.6889 | 0.4556 |
| **Macro F1** | **0.6563** | **0.3898** |

### Confusion Matrix Dağılımları (`[negative, neutral, positive]`)

- **RuleBasedTurkishScorer:**
  ```text
  Gerçek \ Tahmin    Negative    Neutral    Positive
  Negative (30)         8          19          3
  Neutral  (30)         0          30          0
  Positive (30)         0           6         24
  ```

- **BerturkTurkishScorer:**
  ```text
  Gerçek \ Tahmin    Negative    Neutral    Positive
  Negative (30)         6          24          0
  Neutral  (30)         0          30          0
  Positive (30)         0          25          5
  ```

### Bulgular ve Mimari Karar
1. **Nötr Eğilimi:** Hazır eğitilmiş `Omar1010/bert-turkish-sentiment` modeli bu 90 sentetik cümle yapısında hem olumsuz hem de olumlu ifadeleri belirgin biçimde `neutral` olarak sınıflandırma eğilimi göstermiştir.
2. **Kural Tabanlı Skorlayıcının Kararlılığı:** Kural tabanlı yöntem anahtar kelime varlığında olumlu sınıfta (%80 recall, %88.89 precision) daha kararlı davranmıştır.
3. **Güvenli Mimari Kararı:** Bu bulgular ışığında BERTurk ana sıralama karar vericisi olmaktan çıkarılmış; **yalnızca açıkça seçilen deneysel bir analiz modu** (`is_experimental=True`) olarak konumlandırılmıştır. Varsayılan ana sıralama motoru `RuleBasedTurkishScorer` olarak kalmıştır.
4. **Sınırlılık:** Bu sonuçlar yalnızca 90 kurgusal sentetik örnek için geçerlidir; gerçek sosyal medya metinlerindeki genel model performansını temsil etmez. Depoda model fine-tuning çalışması yapılmamıştır.

---

## 6. Test ve Doğrulama

Değerlendirme altyapısı birim testleri ile korunmaktadır:
```powershell
python -m pytest tests/test_evaluation_script.py -v
```

Bu testler;
- CSV veri bütünlüğünü ve 30/30/30 dengesini,
- Saf Python metrik hesaplamasını ve 3x3 confusion matrix sırasını,
- BERTurk model yükleme hatasında sahte metrik üretilmeyip `null` dönüldüğünü,
- JSON ve CSV artifact çıktılarının yapısını,
- Deneysel mod ve şeffaflık etiketlerini
doğrular. Testler ağ veya model indirme bağımlılığı içermez.
