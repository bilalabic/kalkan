from dataclasses import dataclass


@dataclass(frozen=True)
class FlagDef:
    id: str
    category: str
    severity: str
    log_odds_weight: float
    label: str


FLAGS: dict[str, FlagDef] = {f.id: f for f in [
    FlagDef("ODEME_PLATFORM_DISI",           "payment",   "kritik",  3.2, "Platform dışı ödeme"),
    FlagDef("ODEME_SAHTE_DEKONT",            "payment",   "kritik",  3.5, "Sahte dekont"),
    FlagDef("LINK_SAHTE_KARGO",              "link",      "kritik",  3.7, "Sahte kargo linki"),
    FlagDef("LINK_KART_BILGISI",             "link",      "kritik",  3.6, "Kart bilgisi linki"),
    FlagDef("ODEME_KAPORA",                  "payment",   "yuksek",  1.8, "Kapora talebi"),
    FlagDef("ODEME_KRIPTO",                  "payment",   "yuksek",  1.9, "Kripto ödeme"),
    FlagDef("KARGO_UCRET_TUZAGI",            "cargo",     "yuksek",  3.4, "Kargo ücret tuzağı"),
    FlagDef("DAVRANIS_PLATFORM_DISINA_CIKMA","behaviour", "yuksek",  1.7, "Platform dışına çıkma"),
    FlagDef("KIMLIK_IBAN_ISIM_UYUSMAZLIGI",  "identity",  "yuksek",  2.0, "IBAN isim uyuşmazlığı"),
    FlagDef("ODEME_KOMISYON_SOYLEMI",        "payment",   "orta",    1.2, "Komisyon kaçınması"),
    FlagDef("FIYAT_COK_DUSUK",              "price",     "orta",    1.6, "Piyasanın altı fiyat"),
    FlagDef("DAVRANIS_ACILIYET",             "behaviour", "orta",    1.1, "Aciliyet baskısı"),
    FlagDef("DAVRANIS_TUTARSIZ_HIKAYE",      "behaviour", "orta",    1.0, "Tutarsız hikaye"),
    FlagDef("HESAP_GECMISSIZ",              "account",   "orta",    1.4, "Geçmişsiz hesap"),
    FlagDef("ILAN_BELIRSIZ",                "listing",   "dusuk",   0.5, "İlan belirsizliği"),
    FlagDef("WEB_SIKAYET_KAYDI",            "web",       "yuksek",  2.5, "Web şikayet kaydı"),
    FlagDef("PLATFORM_ICI_GUVENCE",         "platform",  "dusuk",  -1.2, "Platform içi güvence"),
    FlagDef("HESAP_KOKLU",                  "account",   "dusuk",  -0.9, "Köklü hesap"),
    FlagDef("KIMLIK_BELGE_TALEBI",          "identity",  "yuksek",  2.1, "Kimlik/selfie talebi"),
    FlagDef("IBAN_YABANCI",                 "identity",  "yuksek",  2.3, "Yabancı IBAN"),
]}

VALID_IDS: frozenset[str] = frozenset(FLAGS)
