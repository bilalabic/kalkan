from __future__ import annotations

import re

_TR_IBAN_RE = re.compile(r"^TR\d{24}$", re.IGNORECASE)


def _mod97(iban: str) -> int:
    rearranged = iban[4:] + iban[:4]
    numeric = "".join(
        str(ord(c) - ord("A") + 10) if c.isalpha() else c for c in rearranged
    )
    return int(numeric) % 97


def validate_iban(iban: str) -> dict:
    """Validate TR IBAN format and mod-97 checksum."""
    if not iban:
        return {"iban": iban, "valid": False, "reason": "Boş IBAN"}

    cleaned = iban.replace(" ", "").replace("-", "").upper()

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
