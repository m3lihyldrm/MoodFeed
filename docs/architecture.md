# Mimari

MoodFeed MVP üç karar katmanından oluşur: yerel duygu/toksisite skorlaması, etkileşimlerden spiral riski ve açıklanabilir yeniden sıralama.

## Veri akışı

`sample_feed.json` içindeki kurgusal içerikler API tarafından okunur. Her içerik kural tabanlı skorlayıcıdan geçer. İstemcinin gönderdiği kimliksiz `negativity_score` değerleri spiral riskini hesaplar. Risk ve içerik skorları sıralama puanına dönüştürülür; sonuçta içerikler, sıra değişikliği gerekçeleriyle JSON olarak döner.

## Skorlama ve risk

Skorlayıcı küçük Türkçe olumlu, olumsuz ve saldırgan ifade sözlükleri kullanır. Tüm değerler 0–1 aralığına sınırlandırılır. Spiral riski, son en fazla 10 etkileşim için `0.6 × olumsuzluk kayan ortalaması + 0.4 × olumsuz etkileşim oranı` formülüyle hesaplanır. 0.60 ve üstü yüksek, 0.35–0.59 orta, daha altı düşük risktir.

## Yeniden sıralama ve şeffaflık

MVP içerik silmez. Açık durumdayken sıralama puanı `original_score - 0.35 × toxicity_score - 0.25 × negativity_score × spiral_risk + 0.15 × diversity_score × spiral_risk` formülüyle hesaplanır. `diversity_score`, olumlu/nötr içerikte 1.0, olumsuz içerikte 0.0'dır. Eşit puanlarda özgün sıra korunur.

Her yanıtta, toksisite cezasını, dengeleyici içeriğin öne çıkarılmasını ya da sıra değişimini açıklayan Türkçe gerekçeler bulunur. `/transparency/{content_id}` son işlenen içeriğin gerekçelerini ayrı olarak verir.

## Kullanıcı kontrolü, gizlilik ve gelecek

`POST /settings/toggle` ayarı değiştirir. Özellik kapalıyken özgün sıra ve özgün sıralama puanı aynen korunur; yanıtta bunun gerekçesi açıkça verilir. Ham metin veya etkileşimler kalıcı saklanmaz; bu sistem klinik tanı koymaz ve otomatik moderasyon değildir.

`ContentScorer` sözleşmesi, ileride değerlendirilmiş yerel BERTurk uyarlamasıyla değiştirilebilir. MVP’de BERTurk eğitimi, gerçek kullanıcı testi ve A/B testi yoktur.
