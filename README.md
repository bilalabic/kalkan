# Kalkan

İkinci el alışveriş yazışmalarında dolandırıcılık tespiti.  
Ekran görüntüsü veya metin yükle — saniyeler içinde risk skoru ve gerekçeli uyarı listesi al.

---

## Ne İşe Yarar?

Sahibinden, Letgo ve benzeri platformlardaki yazışmaları analiz eder. Sahte kargo linkleri, platform dışı ödeme talepleri, kapora sahtekarlığı ve 18 farklı dolandırıcılık örüntüsünü otomatik olarak tespit eder.

---

## Nasıl Çalışır?

Gönderdiğin yazışma beş aşamadan geçer:

**1. Çıkarım** — Yazışmadan kim ne demiş, hangi linkler ve IBAN'lar geçiyor, ürün ve fiyat nedir bunlar ayrıştırılır.

**2. Kural kontrolü** — Linkler sahte domain ve typosquatting için kontrol edilir. IBAN geçerlilik ve checksum doğrulaması yapılır.

**3. Sınıflandırma** — Yapay zeka sabit bir bayrak listesinden hangilerinin geçtiğini tespit eder. Her bayrak için yazışmadan birebir kanıt cümlesi zorunludur; kanıt yoksa bayrak eklenmez.

**4. Doğrulama** — Her bayrağın kanıtı orijinal metinde gerçekten var mı bulanık eşleşme ile kontrol edilir; yoksa bayrak düşürülür.

**5. Risk skoru** — Bayrakların ağırlıkları log-odds formülüyle birleştirilir. Skoru yapay zeka değil, sabit bir matematiksel formül hesaplar.

> **Derin kontrol** seçeneği açılırsa sistem ek olarak Google'da arama yaparak ilgili IBAN, domain ve telefon numaralarının şikayet sitelerinde kaydı olup olmadığını da kontrol eder.

---

## Kurulum

Python 3.11 veya üstü ve bir Gemini API anahtarı gereklidir.

```bash
git clone https://github.com/kullanici/kalkan.git
cd kalkan
pip install -r requirements.txt
```

Proje klasöründe `.env` dosyası oluştur:

```
GEMINI_API_KEY=buraya_api_anahtarini_yaz
```

Sunucuyu başlat:

```bash
uvicorn app.main:app --reload
```

Tarayıcıdan aç: `http://localhost:8000`

---

## Tespit Edilen Örüntüler

| Örüntü | Açıklama |
|--------|----------|
| Sahte kargo linki | araskargo.com.tr veya ptt.gov.tr taklidi domainler |
| Kart bilgisi talebi | Link üzerinden kart numarası, CVV istenmesi |
| Sahte ödeme dekontu | Ödeme yapılmış gibi gösterilen uydurma dekont |
| Platform dışı ödeme | IBAN / havale ile platformun güvencesi atlatılıyor |
| Kapora talebi | Ürün tesliminden önce güvence adı altında para istenmesi |
| Kripto ödeme | Geri alınamaz kripto para transferi talebi |
| Kargo ücreti tuzağı | Paket bekletilerek ek kargo ücreti istenmesi |
| Platform dışına çıkma | WhatsApp, Telegram'a yönlendirme |
| Aciliyet baskısı | "Başkası da istiyor", "bugün satıyorum" kalıpları |
| Piyasa altı fiyat | Gerçek değerin çok altında teklif |
| Web şikayet kaydı | İlgili kişi/domain hakkında şikayet sitesi kaydı |

Ayrıca geçmişsiz hesap, belirsiz ilan, tutarsız hikaye gibi destekleyici sinyaller de değerlendirilir.  
Platform içi güvenceli ödeme ve köklü hesap tespit edildiğinde risk skoru düşürülür.

---

## Değerlendirme

Etiketli test seti üzerinde pipeline'ı çalıştır:

```bash
python eval.py
```

Çıktı: her risk seviyesi için precision/recall/F1, genel doğruluk oranı ve karışıklık matrisi.

---

## Yapılandırma

| Değişken | Varsayılan | Açıklama |
|----------|------------|----------|
| `GEMINI_API_KEY` | — | Zorunlu |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Kullanılan model |
| `THINKING_BUDGET` | `8192` | Düşünme adımı token limiti; 0 kapatır |

---

## Teknik Yığın

- **Backend:** FastAPI, Python 3.11+
- **Yapay Zeka:** Gemini 2.5 Flash — yapılandırılmış çıktı + genişletilmiş düşünme
- **Kural Katmanı:** tldextract (domain analizi), rapidfuzz (bulanık eşleşme)
- **Arayüz:** Tek HTML dosyası — Tailwind + Alpine.js, build adımı yok

## Gizlilik

Yüklenen görseller ve yazışma metinleri yalnızca analiz süresince bellekte tutulur. Diske yazılmaz, üçüncü taraflarla paylaşılmaz. KVKK kapsamında kişisel veri "işle ve at" prensibiyle ele alınır.
