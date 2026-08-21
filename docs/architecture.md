# Mimari

MoodFeed MVP üç karar katmanından oluşur: yerel duygu/toksisite skorlaması, etkileşimlerden spiral riski ve açıklanabilir yeniden sıralama.

## Veri akışı

`sample_feed.json` içindeki kurgusal içerikler API tarafından okunur. Her içerik kural tabanlı skorlayıcıdan geçer. İstemcinin gönderdiği kimliksiz `negativity_score` değerleri spiral riskini hesaplar. Risk ve içerik skorları sıralama puanına dönüştürülür; sonuçta içerikler, sıra değişikliği gerekçeleriyle JSON olarak döner.

## Skorlama ve risk

Skorlayıcı küçük Türkçe olumlu, olumsuz ve saldırgan ifade sözlükleri kullanır. Tüm değerler 0–1 aralığına sınırlandırılır. Spiral riski, son en fazla 10 etkileşim için `0.6 × olumsuzluk kayan ortalaması + 0.4 × olumsuz etkileşim oranı` formülüyle hesaplanır. 0.60 ve üstü yüksek, 0.35–0.59 orta, daha altı düşük risktir.

## Yeniden sıralama, kontrol ve gelecek

MVP içerik silmez. Açık durumdayken toksisite ve riskli olumsuzluk puanı azaltır; yüksek riskte nötr/olumlu içeriğe çeşitlilik bonusu verir. Her karar gerekçesi yanıtta ve `/transparency/{content_id}` adresinde yer alır. Kapalıyken özgün sıra aynen korunur. Ham metin veya etkileşimler kalıcı saklanmaz; bu sistem klinik tanı koymaz. `ContentScorer` sözleşmesi, ileride değerlendirilmiş yerel BERTurk uyarlamasıyla değiştirilebilir. MVP’de BERTurk eğitimi ve gerçek kullanıcı testi yoktur.
