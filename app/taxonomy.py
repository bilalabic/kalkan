from dataclasses import dataclass


@dataclass(frozen=True)
class FlagDef:
    flag_id: str
    title: str
    default_weight: float


FLAGS: dict[str, FlagDef] = {f.flag_id: f for f in [
    FlagDef("URGENCY_PRESSURE",     "Acele / baskı dili",            0.15),
    FlagDef("OFFPLATFORM_REDIRECT", "Platform dışına yönlendirme",   0.20),
    FlagDef("SUSPICIOUS_IBAN",      "Şüpheli IBAN / hesap",          0.25),
    FlagDef("PRICE_TOO_LOW",        "Piyasa altı fiyat",             0.15),
    FlagDef("FAKE_ESCROW",          "Sahte emanet / güvende öde",    0.25),
    FlagDef("IDENTITY_MISMATCH",    "Kimlik tutarsızlığı",           0.20),
    FlagDef("SUSPICIOUS_LINK",      "Şüpheli bağlantı",              0.20),
    FlagDef("ADVANCE_FEE",          "Peşin ücret / komisyon talebi", 0.25),
    FlagDef("NEW_ACCOUNT",          "Yeni / puansız hesap",          0.10),
    FlagDef("CARGO_SCAM",           "Kargo dolandırıcılığı kalıbı",  0.20),
]}
