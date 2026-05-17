from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlparse

import tldextract
from rapidfuzz import fuzz

_WHITELIST: frozenset[str] = frozenset({
    # Kargo şirketleri
    "araskargo.com.tr", "yurticikargo.com", "mngkargo.com.tr",
    "ptt.gov.tr", "suratkargo.com.tr", "trendyolexpress.com",
    "hepsijet.com", "sendeo.com.tr", "scotty.com.tr", "kolikgo.com",
    "horoz.com.tr", "kargoist.com", "bringo.com.tr",
    # Bankalar
    "garantibbva.com.tr", "isbank.com.tr", "akbank.com",
    "yapikredi.com.tr", "ziraatbank.com.tr", "halkbank.com.tr",
    "vakifbank.com.tr", "denizbank.com", "teb.com.tr",
    "ingbank.com.tr", "qnbfinansbank.com", "odeabank.com.tr",
    "fibabanka.com.tr", "burganbank.com.tr", "sekerbank.com.tr",
    "albaraka.com.tr", "kuveytturk.com.tr", "ziraatkatilim.com.tr",
    # Ödeme sistemleri
    "iyzico.com", "paytr.com", "papara.com", "param.com.tr",
    # Pazaryerleri & ikinci el
    "trendyol.com", "n11.com", "hepsiburada.com", "sahibinden.com",
    "letgo.com", "dolap.com", "gittigidiyor.com", "amazon.com.tr",
    "pttavm.com", "pazarama.com", "ciceksepeti.com",
    # Telekomünikasyon (dijital ürün ödemeleri)
    "turkcell.com.tr", "vodafone.com.tr", "turktelekom.com.tr",
})

# URL kısaltıcı servisleri
_URL_SHORTENERS: frozenset[str] = frozenset({
    "bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly", "short.link",
    "kisa.link", "tr.im", "is.gd", "buff.ly", "adf.ly", "rb.gy",
    "cutt.ly", "tiny.cc", "snipurl.com", "shorturl.at",
})

# Dolandırıcılığa özgü riskli TLD'ler
_HIGH_RISK_TLDS: frozenset[str] = frozenset({
    "xyz", "online", "site", "tk", "ml", "cf", "ga", "gq", "pw",
    "click", "link", "work", "loan", "top",
})

# Ödeme/giriş yolu örüntüleri
_SUSPICIOUS_PATH_RE = re.compile(
    r"/(?:odeme|kart(?:[_-]?bilgi)?|havale|payment|giris|login|card|onayla|confirm|verify)",
    re.IGNORECASE,
)

_TYPOSQUATTING_THRESHOLD = 85
_SUBDOMAIN_BRAND_THRESHOLD = 82


def _registered_domain(url: str) -> str:
    ext = tldextract.extract(url)
    if ext.domain and ext.suffix:
        return f"{ext.domain}.{ext.suffix}"
    return ext.domain or url


def _domain_label(url: str) -> str:
    return tldextract.extract(url).domain.lower()


def _subdomain_str(url: str) -> str:
    sub = tldextract.extract(url).subdomain.lower()
    # www ve benzeri teknik subdomain'leri atla
    return "" if sub in ("www", "m", "tr", "en", "api", "cdn") else sub


def _is_ip_url(url: str) -> bool:
    """Gerçek IP adresi URL'si mi? (kargo/banka IP kullanmaz)"""
    try:
        parsed = urlparse(url if "://" in url else "http://" + url)
        host = parsed.hostname or ""
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def _typosquat_score(domain: str, whitelist_entry: str) -> float:
    """Tam domain karşılaştırması + label partial_ratio — ikisinin maksimumu."""
    label = _domain_label(domain)
    wlabel = _domain_label(whitelist_entry)
    full_score = fuzz.ratio(domain, whitelist_entry)
    label_score = fuzz.partial_ratio(label, wlabel) if label and wlabel else 0
    return max(full_score, label_score)


def _best_whitelist_match(domain: str) -> tuple[float, str]:
    return max(
        ((_typosquat_score(domain, w), w) for w in _WHITELIST),
        key=lambda t: t[0],
    )


def _check_subdomain_spoofing(url: str) -> tuple[bool, str, str]:
    """
    ptt.kargo-sahte.com gibi subdomain sahtekarlığı tespiti.
    Marka adı sahte bir domainin subdomain'i olarak ekleniyor.
    Döndürür: (bulundu_mu, whitelist_eşleşmesi, subdomain_string)
    """
    sub = _subdomain_str(url)
    if not sub:
        return False, "", ""
    best_score = 0.0
    best_match = ""
    for w in _WHITELIST:
        wlabel = _domain_label(w)
        score = fuzz.partial_ratio(sub, wlabel)
        if score > best_score:
            best_score = score
            best_match = w
    if best_score >= _SUBDOMAIN_BRAND_THRESHOLD:
        return True, best_match, sub
    return False, "", ""


def check_domain(url: str) -> dict:
    """
    URL için durum (guvenli/sahte/supheli) ve Türkçe gerekçe döndürür.

    Kontrol sırası:
    1. IP adresi URL → sahte
    2. Whitelist tam eşleşme → guvenli
    3. URL kısaltıcı → supheli
    4. Subdomain marka sahtekarlığı → sahte
    5. Typosquatting ≥ 85 → sahte
    6. Riskli TLD + marka benzerliği ≥ 55 → sahte
    7. Şüpheli ödeme/giriş yolu → supheli
    8. Diğer → supheli
    """
    if not url or not url.strip():
        return {"url": url, "domain": "", "status": "supheli", "reason": "Boş URL"}

    # 1. IP adresi URL
    if _is_ip_url(url):
        return {
            "url": url,
            "domain": url,
            "status": "sahte",
            "reason": "IP adresi URL'si — gerçek kargo/banka siteleri domain adı kullanır.",
        }

    domain = _registered_domain(url)
    ext = tldextract.extract(url)
    has_suspicious_path = bool(_SUSPICIOUS_PATH_RE.search(url))

    # 2. Whitelist tam eşleşme
    if domain in _WHITELIST:
        extra = " — URL'de ödeme/giriş yolu var, dikkatli olun." if has_suspicious_path else ""
        return {
            "url": url,
            "domain": domain,
            "status": "guvenli",
            "reason": f"{domain} güvenilir domain listesinde{extra}",
        }

    # 3. URL kısaltıcı
    if domain in _URL_SHORTENERS:
        return {
            "url": url,
            "domain": domain,
            "status": "supheli",
            "reason": f"Kısaltılmış bağlantı ({domain}) — hedef adres gizlenmiş, tıklamadan doğrulayın.",
        }

    # 4. Subdomain marka sahtekarlığı (ptt.kargo-sahte.com)
    spoofed, spoof_match, spoof_sub = _check_subdomain_spoofing(url)
    if spoofed:
        return {
            "url": url,
            "domain": domain,
            "status": "sahte",
            "reason": (
                f"Subdomain sahtekarlığı: '{spoof_sub}' markası '{domain}' adlı sahte "
                f"domainin alt alanı yapılmış (gerçek site: {spoof_match})"
            ),
            "typosquat_of": spoof_match,
        }

    # 5. Typosquatting
    best_score, best_match = _best_whitelist_match(domain)
    if best_score >= _TYPOSQUATTING_THRESHOLD:
        return {
            "url": url,
            "domain": domain,
            "status": "sahte",
            "reason": f"Typosquatting: '{domain}' → '{best_match}' (benzerlik %{best_score:.0f})",
            "typosquat_of": best_match,
        }

    # 6. Riskli TLD + marka benzerliği
    if ext.suffix in _HIGH_RISK_TLDS and best_score >= 55:
        return {
            "url": url,
            "domain": domain,
            "status": "sahte",
            "reason": (
                f"Riskli uzantı (.{ext.suffix}) + marka benzerliği: "
                f"'{domain}' ≈ '{best_match}' (%{best_score:.0f})"
            ),
            "typosquat_of": best_match,
        }

    # 7. Şüpheli ödeme/giriş yolu (bilinmeyen domain üzerinde)
    if has_suspicious_path:
        return {
            "url": url,
            "domain": domain,
            "status": "supheli",
            "reason": f"'{domain}' güvenilir listede değil ve URL ödeme/giriş yolu içeriyor.",
        }

    # 8. Genel şüpheli
    return {
        "url": url,
        "domain": domain,
        "status": "supheli",
        "reason": f"'{domain}' güvenilir kargo/banka domain listesinde değil",
    }
