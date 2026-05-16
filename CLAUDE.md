# Kalkan — Pazaryeri Dolandırıcılık Tespiti

## Bağlam
Türkiye ikinci el/sosyal ticaret yazışmalarında dolandırıcılık tespiti.
Kullanıcı ekran görüntüsü/metin yükler -> risk skoru + gerekçeli bayrak listesi.
Hackathon: tek kişi, 48 saat, web uygulaması.

## Stack — SADECE bunlar
- FastAPI + uvicorn
- google-genai SDK (from google import genai)
- Model: gemini-2.5-flash. ASLA gemini-2.0-* (1 Haziran 2026'da kapanıyor).
- Pydantic v2 + Gemini structured output (response_schema)
- rapidfuzz, tldextract, python-multipart
- Frontend: tek static/index.html, Tailwind CDN + Alpine.js CDN

## KULLANMA — önerme, ekleme
LangChain/LangGraph/CrewAI, vektör DB, veritabani/ORM, Docker Compose,
JWT/giris, MCP sunucu framework'u. Hepsi kapsam disi.

## Mimari — 5 asamali hat
extract -> deterministic -> classify -> verify -> fusion (log-odds)

## Cekirdek kural
- Bayrak ID'leri taxonomy.py'de sabit; LLM serbest baslik uretmez.
- Risk skorunu fusion.py hesaplar, LLM degil.
- schemas.py tek dogruluk kaynagi (API yaniti + Gemini semasi).
- Urun "yuksek risk" der, "dolandirici" demez.
- Kisisel veri isle-ve-at, kalici saklama yok (KVKK).