from dataclasses import dataclass


@dataclass(frozen=True)
class BayrakTanim:
    id: str
    kategori: str
    severity: str          # "kritik" | "yuksek" | "orta" | "dusuk"
    log_odds_weight: float  # pozitif = suç yönünde, negatif = aklayıcı


# Tek düzenleme noktası — tüm bayraklar burada.
BAYRAKLAR: dict[str, BayrakTanim] = {b.id: b for b in [
    # ── Kritik ──────────────────────────────────────────────────────────
    BayrakTanim("ODEME_PLATFORM_DISI",        "odeme",    "kritik",  3.2),
    BayrakTanim("ODEME_SAHTE_DEKONT",         "odeme",    "kritik",  3.5),
    BayrakTanim("LINK_SAHTE_KARGO",           "link",     "kritik",  3.7),
    BayrakTanim("LINK_KART_BILGISI",          "link",     "kritik",  3.6),
    # ── Yüksek ──────────────────────────────────────────────────────────
    BayrakTanim("ODEME_KAPORA",               "odeme",    "yuksek",  1.8),
    BayrakTanim("ODEME_KRIPTO",               "odeme",    "yuksek",  1.9),
    BayrakTanim("KARGO_UCRET_TUZAGI",         "kargo",    "yuksek",  3.4),
    BayrakTanim("DAVRANIS_PLATFORM_DISINA_CIKMA", "davranis", "yuksek", 1.7),
    BayrakTanim("KIMLIK_IBAN_ISIM_UYUSMAZLIGI", "kimlik", "yuksek",  2.0),
    # ── Orta ────────────────────────────────────────────────────────────
    BayrakTanim("ODEME_KOMISYON_SOYLEMI",     "odeme",    "orta",    1.2),
    BayrakTanim("FIYAT_COK_DUSUK",            "fiyat",    "orta",    1.6),
    BayrakTanim("DAVRANIS_ACILIYET",          "davranis", "orta",    1.1),
    BayrakTanim("DAVRANIS_TUTARSIZ_HIKAYE",   "davranis", "orta",    1.0),
    BayrakTanim("HESAP_GECMISSIZ",            "hesap",    "orta",    1.4),
    # ── Düşük ───────────────────────────────────────────────────────────
    BayrakTanim("ILAN_BELIRSIZ",              "ilan",     "dusuk",   0.5),
    # ── Aklayıcı sinyaller (negatif ağırlık) ────────────────────────────
    BayrakTanim("PLATFORM_ICI_GUVENCE",       "platform", "dusuk",  -1.2),
    BayrakTanim("HESAP_KOKLU",                "hesap",    "dusuk",  -0.9),
]}

# Hızlı erişim yardımcıları
GECERLI_IDS: frozenset[str] = frozenset(BAYRAKLAR)
