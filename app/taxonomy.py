from dataclasses import dataclass


@dataclass(frozen=True)
class FlagDef:
    id: str
    category: str
    severity: str
    log_odds_weight: float


FLAGS: dict[str, FlagDef] = {f.id: f for f in [
    FlagDef("ODEME_PLATFORM_DISI",           "payment",   "kritik",  3.2),
    FlagDef("ODEME_SAHTE_DEKONT",            "payment",   "kritik",  3.5),
    FlagDef("LINK_SAHTE_KARGO",              "link",      "kritik",  3.7),
    FlagDef("LINK_KART_BILGISI",             "link",      "kritik",  3.6),
    FlagDef("ODEME_KAPORA",                  "payment",   "yuksek",  1.8),
    FlagDef("ODEME_KRIPTO",                  "payment",   "yuksek",  1.9),
    FlagDef("KARGO_UCRET_TUZAGI",            "cargo",     "yuksek",  3.4),
    FlagDef("DAVRANIS_PLATFORM_DISINA_CIKMA","behaviour", "yuksek",  1.7),
    FlagDef("KIMLIK_IBAN_ISIM_UYUSMAZLIGI",  "identity",  "yuksek",  2.0),
    FlagDef("ODEME_KOMISYON_SOYLEMI",        "payment",   "orta",    1.2),
    FlagDef("FIYAT_COK_DUSUK",              "price",     "orta",    1.6),
    FlagDef("DAVRANIS_ACILIYET",             "behaviour", "orta",    1.1),
    FlagDef("DAVRANIS_TUTARSIZ_HIKAYE",      "behaviour", "orta",    1.0),
    FlagDef("HESAP_GECMISSIZ",              "account",   "orta",    1.4),
    FlagDef("ILAN_BELIRSIZ",                "listing",   "dusuk",   0.5),
    FlagDef("WEB_SIKAYET_KAYDI",            "web",       "yuksek",  2.5),
    FlagDef("PLATFORM_ICI_GUVENCE",         "platform",  "dusuk",  -1.2),
    FlagDef("HESAP_KOKLU",                  "account",   "dusuk",  -0.9),
]}

VALID_IDS: frozenset[str] = frozenset(FLAGS)
