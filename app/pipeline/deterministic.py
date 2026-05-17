from __future__ import annotations

from app.schemas import ExtractOutput, Flag, LinkAnalysis
from app.tools.domain_check import check_domain
from app.tools.iban_check import validate_iban


def run_deterministic(extracted: ExtractOutput) -> tuple[list[Flag], list[LinkAnalysis]]:
    """Stage 2: rule-based flag detection, no LLM."""
    flags: list[Flag] = []
    link_analysis: list[LinkAnalysis] = []
    seen: set[str] = set()

    # ── URL kontrolleri ────────────────────────────────────────────────────
    fake_urls: list[str] = []
    for url in extracted.urls:
        result = check_domain(url)
        link_analysis.append(LinkAnalysis(
            url=url,
            status=result["status"],
            reason=result["reason"],
        ))
        if result["status"] == "sahte":
            fake_urls.append(url)

    if fake_urls and "LINK_SAHTE_KARGO" not in seen:
        flags.append(Flag(
            id="LINK_SAHTE_KARGO",
            category="link",
            evidence=", ".join(fake_urls),
            description=(
                f"{len(fake_urls)} sahte domain tespit edildi: "
                + check_domain(fake_urls[0])["reason"]
            )[:120],
        ))
        seen.add("LINK_SAHTE_KARGO")

    # ── IBAN kontrolleri ───────────────────────────────────────────────────
    for iban in extracted.ibans:
        result = validate_iban(iban)
        if result.get("valid"):
            continue

        # Yabancı IBAN → ayrı, daha ağır flag
        if result.get("foreign") and "IBAN_YABANCI" not in seen:
            flags.append(Flag(
                id="IBAN_YABANCI",
                category="identity",
                evidence=iban,
                description=result["reason"][:120],
            ))
            seen.add("IBAN_YABANCI")

        # Geçersiz/checksum hatası → format/kimlik uyuşmazlığı
        elif not result.get("foreign") and "KIMLIK_IBAN_ISIM_UYUSMAZLIGI" not in seen:
            flags.append(Flag(
                id="KIMLIK_IBAN_ISIM_UYUSMAZLIGI",
                category="identity",
                evidence=iban,
                description=result["reason"][:120],
            ))
            seen.add("KIMLIK_IBAN_ISIM_UYUSMAZLIGI")

    return flags, link_analysis
