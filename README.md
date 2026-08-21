# MoodFeed

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
