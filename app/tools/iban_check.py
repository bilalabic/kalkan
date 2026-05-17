from __future__ import annotations

import re

_TR_IBAN_RE = re.compile(r"^TR\d{24}$", re.IGNORECASE)
_IBAN_COUNTRY_RE = re.compile(r"^([A-Z]{2})\d{2}", re.IGNORECASE)


def _mod97(iban: str) -> int:
    rearranged = iban[4:] + iban[:4]
    numeric = "".join(
        str(ord(c) - ord("A") + 10) if c.isalpha() else c for c in rearranged
    )
    return int(numeric) % 97


def validate_iban(iban: str) -> dict:
    """Validate TR IBAN format and mod-97 checksum. Detect foreign IBANs."""
    if not iban:
        return {"iban": iban, "valid": False, "reason": "Boş IBAN"}

    cleaned = iban.replace(" ", "").replace("-", "").upper()

    # Yabancı IBAN tespiti: TR dışı ülke kodu ile başlıyor
    country_match = _IBAN_COUNTRY_RE.match(cleaned)
    if country_match and country_match.group(1) != "TR":
        country = country_match.group(1)
        return {
            "iban": iban,
            "valid": False,
            "foreign": True,
            "reason": (
                f"Yabancı IBAN ({country}) — Türkiye'deki satıcı yabancı banka hesabı "
                f"kullanıyor; kara para aklamanın yaygın yöntemi."
            ),
        }

    if not _TR_IBAN_RE.match(cleaned):
        return {
            "iban": iban,
            "valid": False,
            "reason": (
                f"Format hatası: TR IBAN 'TR' + 24 rakam olmalı "
                f"(alınan: '{cleaned}', uzunluk: {len(cleaned)})"
            ),
        }

    remainder = _mod97(cleaned)
    if remainder != 1:
        return {
            "iban": iban,
            "valid": False,
            "reason": f"Checksum hatası: mod-97 = {remainder}, beklenen 1",
        }

    return {"iban": iban, "valid": True, "reason": "Geçerli TR IBAN"}
