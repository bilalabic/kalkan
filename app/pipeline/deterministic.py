from __future__ import annotations

from app.schemas import ExtractOutput, Flag, LinkAnalysis
from app.tools.domain_check import check_domain
from app.tools.iban_check import validate_iban


def run_deterministic(extracted: ExtractOutput) -> tuple[list[Flag], list[LinkAnalysis]]:
    """Stage 2: rule-based flag detection, no LLM."""
    flags: list[Flag] = []
    link_analysis: list[LinkAnalysis] = []
    seen: set[str] = set()

    for url in extracted.urls:
        result = check_domain(url)
        link_analysis.append(LinkAnalysis(
            url=url,
            status=result["status"],
            reason=result["reason"],
        ))
        if result["status"] == "sahte" and "LINK_SAHTE_KARGO" not in seen:
            flags.append(Flag(
                id="LINK_SAHTE_KARGO",
                category="link",
                evidence=url,
                description=result["reason"],
            ))
            seen.add("LINK_SAHTE_KARGO")

    for iban in extracted.ibans:
        result = validate_iban(iban)
        if not result["valid"] and "KIMLIK_IBAN_ISIM_UYUSMAZLIGI" not in seen:
            flags.append(Flag(
                id="KIMLIK_IBAN_ISIM_UYUSMAZLIGI",
                category="identity",
                evidence=iban,
                description=result["reason"],
            ))
            seen.add("KIMLIK_IBAN_ISIM_UYUSMAZLIGI")

    return flags, link_analysis
