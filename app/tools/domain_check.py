from __future__ import annotations

import tldextract
from rapidfuzz import fuzz

_WHITELIST: frozenset[str] = frozenset({
    "araskargo.com.tr", "yurticikargo.com", "mngkargo.com.tr",
    "ptt.gov.tr", "suratkargo.com.tr", "trendyolexpress.com",
    "hepsijet.com", "sendeo.com.tr", "scotty.com.tr", "kolikgo.com",
    "garantibbva.com.tr", "isbank.com.tr", "akbank.com",
    "yapikredi.com.tr", "ziraatbank.com.tr", "halkbank.com.tr",
    "vakifbank.com.tr", "denizbank.com", "teb.com.tr",
    "ingbank.com.tr", "qnbfinansbank.com", "odeabank.com.tr",
    "fibabanka.com.tr", "burganbank.com.tr", "sekerbank.com.tr",
    "trendyol.com", "n11.com", "hepsiburada.com", "sahibinden.com",
    "letgo.com", "dolap.com", "gittigidiyor.com", "amazon.com.tr",
})

_TYPOSQUATTING_THRESHOLD = 85


def _registered_domain(url: str) -> str:
    ext = tldextract.extract(url)
    if ext.domain and ext.suffix:
        return f"{ext.domain}.{ext.suffix}"
    return ext.domain or url


def _domain_label(url: str) -> str:
    """Return just the domain label without TLD (e.g. 'araskargo' from 'araskargo.com.tr')."""
    return tldextract.extract(url).domain.lower()


def _typosquat_score(domain: str, whitelist_entry: str) -> float:
    """Score combining full-domain ratio and label partial_ratio for robustness."""
    label = _domain_label(domain)
    wlabel = _domain_label(whitelist_entry)
    full_score = fuzz.ratio(domain, whitelist_entry)
    label_score = fuzz.partial_ratio(label, wlabel) if label and wlabel else 0
    return max(full_score, label_score)


def check_domain(url: str) -> dict:
    """Return status (guvenli/sahte/supheli) and Turkish reason for a URL."""
    if not url or not url.strip():
        return {"url": url, "domain": "", "status": "supheli", "reason": "Boş URL"}

    domain = _registered_domain(url)

    if domain in _WHITELIST:
        return {
            "url": url,
            "domain": domain,
            "status": "guvenli",
            "reason": f"{domain} güvenilir domain listesinde",
        }

    best_score, best_match = max(
        ((_typosquat_score(domain, w), w) for w in _WHITELIST),
        key=lambda t: t[0],
    )

    if best_score >= _TYPOSQUATTING_THRESHOLD:
        return {
            "url": url,
            "domain": domain,
            "status": "sahte",
            "reason": f"Typosquatting: '{domain}' → '{best_match}' (benzerlik %{best_score:.0f})",
            "typosquat_of": best_match,
        }

    return {
        "url": url,
        "domain": domain,
        "status": "supheli",
        "reason": f"'{domain}' güvenilir kargo/banka domain listesinde değil",
    }
