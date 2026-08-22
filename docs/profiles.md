# MoodFeed Akış Kontrol Merkezi & Profil Ağırlıkları Dokümantasyonu

Bu belge, MoodFeed MVP bünyesindeki **Akış Kontrol Merkezi** profillerini, kullanılan matematiksel sıralama formülünü ve katsayı denetimlerini detaylandırmaktadır.

---

## 1. Sıralama Formülü (Reranking Formula)

MoodFeed, sosyal medya içeriklerini **hiçbir zaman silmez**; kullanıcı tarafından seçilen profil doğrultusunda şeffaf ve deterministik bir sıralama puanı (`ranking_score`) hesaplar.

$$\text{ranking\_score} = \text{clamp}\Big(S_{\text{orig}} - (W_{\text{tox}} \times T) - (W_{\text{neg}} \times N \times R) + (W_{\text{div}} \times D \times R)\Big)$$

### Formül Değişkenleri:
- **$S_{\text{orig}}$ (`original_score`):** İçeriğin platformdaki ilk sıralama skoru ($[0.0, 1.0]$).
- **$T$ (`toxicity_score`):** İçerikte tespit edilen toksisite/saldırganlık oranı ($[0.0, 1.0]$).
- **$N$ (`negativity_score`):** İçerikteki olumsuz duygu ve risk skoru ($[0.0, 1.0]$).
- **$R$ (`spiral_risk.score`):** İstemcinin son etkileşim geçmişinden hesaplanan olumsuzluk sarmalı risk katsayısı ($[0.0, 1.0]$).
- **$D$ (`diversity`):** Dengeleyici içerik çarpanı (Toksisite $T=0$ ve duygu etiketi `positive` veya `neutral` ise $1.0$, toksik ($T>0$) veya `negative` ise $0.0$).
- **$\text{clamp}(x)$:** Değeri $[0.0, 1.0]$ aralığına sınırlayan ve 3 ondalık basamağa yuvarlayan fonksiyon.

---

## 2. Profil Katsayıları (User Preference Weights)

Katsayılar "bilimsel optimum" olarak değil, **kullanıcı tercih ağırlıkları** olarak yapılandırılmıştır:

| Profil | Kod | $W_{\text{tox}}$ (Toksisite Cezası) | $W_{\text{neg}}$ (Negatiflik Cezası) | $W_{\text{div}}$ (Çeşitlilik Bonusu) | Açıklama |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Dengeli** *(Varsayılan)* | `balanced` | `0.35` | `0.25` | `0.15` | Standart duygu, toksisite ve risk dengesi. |
| **Daha Sakin Akış** | `calmer` | `0.50` | `0.40` | `0.25` | Toksisite ve olumsuzluk sinyallerine karşı daha hassas filtreleme. |
| **Kullanıcı Kontrolü** | `user_control` | `0.15` | `0.10` | `0.05` | Minimum algoritmik müdahale ile orijinal akışa en yakın sıralama. |

---

## 3. Matematiksel Doğrulama ve Bileşen Dağılımı (Örnek Akış)

Örnek veri kümesi (`sample_feed.json`) ve $R=0.0$ (başlangıç durumu) için bileşen dökümü:

| İçerik ID | Ham Skor ($S_{\text{orig}}$) | Duygu / Toksisite | Dengeli (`balanced`) Puan & Sıra | Daha Sakin (`calmer`) Puan & Sıra | Kullanıcı Kontrolü (`user_control`) Puan & Sıra |
| :--- | :---: | :--- | :---: | :---: | :---: |
| **`post-002`** | `0.82` | Negative / Tox: 0.00 | **0.820** (#1) | **0.820** (#1) | **0.820** (#1) |
| **`post-001`** | `0.65` | Positive / Tox: 0.00 | **0.650** (#2) | **0.650** (#2) | **0.650** (#3) |
| **`post-003`** | `0.58` | Positive / Tox: 0.00 | **0.580** (#3) | **0.580** (#3) | **0.580** (#4) |
| **`post-004`** | `0.78` | Neutral / Tox: 0.70 | **0.535** (#4) | **0.430** (#4) | **0.675** (#2) |

### Gözlemler:
1. **`calmer` Etkisi:** `post-004` için toksisite cezası $0.35 \times 0.70 = 0.245$'ten $0.50 \times 0.70 = 0.350$'e çıkar ve puanı `0.430`'a düşer.
2. **`user_control` Etkisi:** `post-004` için toksisite cezası $0.15 \times 0.70 = 0.105$'e iner, puanı `0.675` olur ve ilk puanı yüksek olduğu için 2. sıraya yükselir.
3. **Determinizm:** Tüm profillerde içerik sayısı ($N=4$) ve içerik kimlikleri korunur; hiçbir içerik silinmez.

---

## 4. Güvenlik ve Gizlilik Prensipleri
- **Kişisel Veri Saklanmaz:** Profil seçimi ve geri alma durumları yalnızca oturum içi bellekte tutulur; veritabanı veya `localStorage`'a kişisel veri yazılmaz.
- **Şeffaf Açıklanabilirlik:** Her sıralama kararı için kural veya model bazlı gerekçeler (`reason`) kullanıcıya sunulur.

---

## 5. Jüri Demosu: Simüle Edilmiş Yüksek Olumsuzluk Senaryosu

- **Amaç:** Formüldeki risk çarpanının ($R$) ve çeşitlilik bonusunun ($W_{\text{div}} \times D \times R$) canlı çalışma etkisini göstermek.
- **Parametre:** `GET /feed?scenario=high_negativity`
- **Sentetik Nitelik:** Bu senaryo yalnızca seçildiğinde istek kapsamında 2 adet sentetik etkileşim (`negativity_score=0.85`) simüle eder. Gerçek kullanıcı ruh hâlini veya klinik bir durumu temsil etmez.
- **Sonuç:** $R \approx 0.85$ seviyesine yükseldiğinde, olumlu içerikler (`post-001`, `post-003`) çeşitlilik bonusu alarak öne geçer; olumsuz içerik (`post-002`) sarmal riski cezası alarak geriye çekilir.
