# Mimari

MoodFeed MVP üç karar katmanından oluşur: yerel duygu/toksisite skorlaması, etkileşimlerden spiral riski ve açıklanabilir yeniden sıralama.

## Veri akışı

`sample_feed.json` içindeki kurgusal içerikler API tarafından okunur. Akış şu sırayı izler: **örnek veri → duygu/tone skoru → toksisite skoru → spiral risk → sıralama puanı → yeniden sıralama → Türkçe açıklama**. İstemcinin gönderdiği kimliksiz `negativity_score` değerleri spiral riskini hesaplar; sonuçta içerikler, sıra değişikliği gerekçeleriyle JSON olarak döner.

## Skorlama ve risk

Skorlayıcı küçük Türkçe olumlu, olumsuz ve saldırgan ifade sözlükleri kullanır. Tüm değerler 0–1 aralığına sınırlandırılır. Spiral riski, son en fazla 10 etkileşim için `0.6 × olumsuzluk kayan ortalaması + 0.4 × olumsuz etkileşim oranı` formülüyle hesaplanır. 0.60 ve üstü yüksek, 0.35–0.59 orta, daha altı düşük risktir.

## Yeniden sıralama ve şeffaflık

MVP içerik silmez. Açık durumdayken sıralama puanı `original_score - 0.35 × toxicity_score - 0.25 × negativity_score × spiral_risk + 0.15 × diversity_score × spiral_risk` formülüyle hesaplanır. Bu katsayılar MVP için başlangıç değerleridir. `diversity_score`, olumlu/nötr içerikte 1.0, olumsuz içerikte 0.0'dır. Eşit puanlarda özgün sıra korunur.

Her yanıtta, toksisite cezasını, dengeleyici içeriğin öne çıkarılmasını ya da sıra değişimini açıklayan Türkçe gerekçeler bulunur. `/transparency/{content_id}` son işlenen içeriğin gerekçelerini ayrı olarak verir.

## Kullanıcı kontrolü, gizlilik ve gelecek

`POST /settings/toggle` ayarı değiştirir. Özellik kapalıyken özgün sıra ve özgün sıralama puanı aynen korunur; yanıtta bunun gerekçesi açıkça verilir. Ham metin veya etkileşimler kalıcı saklanmaz; bu sistem klinik tanı koymaz ve otomatik moderasyon değildir.

`ContentScorer` sözleşmesi hem varsayılan `RuleBasedTurkishScorer` hem de opsiyonel `BerturkTurkishScorer` sağlayıcısını destekler. BERTurk sağlayıcısı hazır fine-tuned model (`Omar1010/bert-turkish-sentiment`) üzerinden duygu çıkarımı yapar. BERTurk bir toksisite modeli olmadığı için toksisite analizi kural tabanlı sözlük ile hibrit olarak yürütülür. Model veya ML kütüphaneleri bulunamazsa sistem hata vermeden kural tabanlı yönteme otomatik fallback yapar. Depoda özel model eğitimi veya metrik iddiası bulunmamaktadır.
