"""Stage 3: LLM classification → ClassifyOutput (flag IDs from taxonomy).

Optional deep-check (deep=True): enables Google Search grounding and registers
check_domain as a function tool so the model can verify URLs and IBANs against
online complaint records. Falls back gracefully if the search call fails.
"""
from __future__ import annotations

import json
import logging
import pathlib
import re

from google import genai
from google.genai import types

from app.config import settings
from app.schemas import ClassifyOutput, ExtractOutput, Flag
from app.taxonomy import FLAGS, VALID_IDS
from app.tools.domain_check import check_domain

# Türk cep telefonu numarası örüntüsü (05xx veya +905xx)
_PHONE_RE = re.compile(
    r'(?<!\d)(?:0|\+90)?[- ]?5\d{2}[- ]?\d{3}[- ]?\d{2}[- ]?\d{2}(?!\d)'
)

logger = logging.getLogger(__name__)

_PROMPT_PATH = pathlib.Path(__file__).parent.parent / "prompts" / "classify.txt"
# Read once at import time — avoids repeated disk I/O on every request.
_PROMPT_TEMPLATE: str = _PROMPT_PATH.read_text(encoding="utf-8")

_client = genai.Client(api_key=settings.gemini_api_key)

_cfg_standard = types.GenerateContentConfig(
    response_mime_type="application/json",
    response_schema=ClassifyOutput,
    thinking_config=types.ThinkingConfig(thinking_budget=settings.thinking_budget),
)

_check_domain_tool = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="check_domain",
            description=(
                "Checks whether a URL's domain is on the trusted whitelist "
                "or is a typosquatting attempt against a known cargo/bank domain."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "url": types.Schema(type=types.Type.STRING, description="URL to check")
                },
                required=["url"],
            ),
        )
    ]
)

_google_search_tool = types.Tool(google_search=types.GoogleSearch())


def _build_prompt(extracted: ExtractOutput) -> str:
    template = _PROMPT_TEMPLATE
    flag_block = "\n".join(
        f"  {fid} ({FLAGS[fid].severity}, weight: {FLAGS[fid].log_odds_weight:+.1f})"
        for fid in sorted(VALID_IDS)
    )
    conversation = "\n".join(extracted.turns)
    if extracted.urls:
        conversation += "\n\nURLs: " + ", ".join(extracted.urls)
    if extracted.ibans:
        conversation += "\nIBANs: " + ", ".join(extracted.ibans)
    if extracted.price:
        conversation += f"\nPrice: {extracted.price}"
    if extracted.product:
        conversation += f"\nProduct: {extracted.product}"
    return (
        template
        .replace("{flag_ids}", flag_block)
        .replace("{conversation}", conversation)
    )


def _parse_response(text: str | None) -> ClassifyOutput:
    if not text:
        return _fallback()
    try:
        return ClassifyOutput.model_validate_json(text)
    except Exception:
        try:
            return ClassifyOutput.model_validate_json(text[text.index("{"):])
        except Exception as exc:
            logger.warning("classify: JSON parse error: %s", exc)
            return _fallback()


def _fallback() -> ClassifyOutput:
    return ClassifyOutput(
        verdict="Analiz tamamlanamadı — lütfen manuel kontrol yapın.",
        flags=[],
        recommended_actions=[
            "Karşı tarafın kimliğini doğrulayın.",
            "Platform dışı ödeme yapmayın.",
            "Şüpheli durumlarda platformun destek hattını arayın.",
        ],
    )


def _filter_flags(flags: list[Flag]) -> list[Flag]:
    """Drop flag IDs not present in the taxonomy (hallucinated by LLM)."""
    valid = [f for f in flags if f.id in VALID_IDS]
    dropped = [f.id for f in flags if f.id not in VALID_IDS]
    if dropped:
        logger.warning("classify: dropped unknown flag IDs: %s", dropped)
    return valid


async def classify_stream(extracted: ExtractOutput, deep: bool = False):
    """Async generator: yields ('thinking', str) chunks, then ('result', ClassifyOutput)."""
    prompt = _build_prompt(extracted)
    full_text = ""

    try:
        stream = await _client.aio.models.generate_content_stream(
            model=settings.gemini_model,
            contents=prompt,
            config=_cfg_standard,
        )
        async for chunk in stream:
            for candidate in (chunk.candidates or []):
                if not candidate.content:
                    continue
                for part in candidate.content.parts or []:
                    if getattr(part, "thought", False):
                        if part.text:
                            yield "thinking", part.text
                    elif part.text:
                        full_text += part.text
    except Exception as exc:
        logger.error("classify_stream: %s", exc)
        yield "error", exc
        return

    result = _parse_response(full_text)
    result.flags = _filter_flags(result.flags)

    if deep and (extracted.urls or extracted.ibans):
        try:
            result = await _deep_check(extracted, result)
        except Exception as exc:
            logger.warning("classify_stream: deep check failed: %s", exc)

    yield "result", result


async def classify(extracted: ExtractOutput, deep: bool = False) -> ClassifyOutput:
    prompt = _build_prompt(extracted)
    try:
        response = await _client.aio.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=_cfg_standard,
        )
        result = _parse_response(response.text)
        result.flags = _filter_flags(result.flags)
    except Exception as exc:
        logger.error("classify: Gemini call failed: %s", exc)
        result = _fallback()

    if deep and (extracted.urls or extracted.ibans):
        try:
            result = await _deep_check(extracted, result)
        except Exception as exc:
            logger.warning("classify: deep check failed (continuing): %s", exc)

    return result


def _extract_phones(turns: list[str]) -> list[str]:
    """Yazışmadan Türk cep telefonu numaralarını çıkar."""
    seen: set[str] = set()
    phones: list[str] = []
    for turn in turns:
        for m in _PHONE_RE.finditer(turn):
            normalized = re.sub(r"[^0-9+]", "", m.group())
            if normalized not in seen:
                seen.add(normalized)
                phones.append(normalized)
    return phones


async def _deep_check(extracted: ExtractOutput, base: ClassifyOutput) -> ClassifyOutput:
    """
    Google Search ile şikayet kaydı ara; bulunursa WEB_SIKAYET_KAYDI bayrağı ekle.

    İyileştirmeler:
    - Yazışmadan telefon numaraları da çıkarılır
    - Her varlık (URL, IBAN, telefon) için ayrı arama yönergesi
    - Türkçe şikayet sitelerine odaklanan arama sorguları
    """
    phones = _extract_phones(extracted.turns)
    all_entities = extracted.urls + extracted.ibans + phones

    if not all_entities:
        return base

    entity_lines = "\n".join(f"- {e}" for e in all_entities)

    # Sadece Google Search — function declaration ile aynı istekte kullanılamaz.
    # Domain kontrolü deterministik aşamada zaten yapılıyor.
    cfg_deep = types.GenerateContentConfig(tools=[_google_search_tool])

    # Ask for structured JSON so we don't do fragile text-matching on the response.
    json_prompt = (
        "Aşağıdaki her varlık için Türkçe şikayet sitelerinde Google araması yap.\n"
        "Hedef siteler: şikayetvar.com, dolandirici.com, Ekşi Sözlük, forumlarda uyarılar.\n\n"
        "Kontrol listesi:\n"
        f"{entity_lines}\n\n"
        "Her varlık için '\"[varlık] dolandırıcı şikayet\"' ve '\"[varlık] sahte güvenilir mi\"' ara.\n\n"
        "Sonucu YALNIZCA şu JSON formatında döndür (başka hiçbir şey yazma):\n"
        '{"found": true|false, "entity": "<şikayetli varlık veya boş string>", '
        '"source": "<kaynak site>", "summary": "<max 120 karakter özet>"}'
    )

    resp = await _client.aio.models.generate_content(
        model=settings.gemini_model,
        contents=[json_prompt],
        config=cfg_deep,
    )

    response_text = (resp.text or "").strip()
    try:
        # Strip markdown code fences if model wraps the JSON.
        clean = re.sub(r"^```(?:json)?\s*|\s*```$", "", response_text, flags=re.DOTALL).strip()
        parsed = json.loads(clean)
        complaint_found = bool(parsed.get("found"))
        complaint_entity = str(parsed.get("entity") or next(iter(all_entities), ""))
        complaint_source = str(parsed.get("source") or "")
        complaint_summary = str(parsed.get("summary") or "")
    except Exception as parse_exc:
        logger.warning("_deep_check: JSON parse failed (%s); raw=%s", parse_exc, response_text[:200])
        complaint_found = False
        complaint_entity = ""
        complaint_source = ""
        complaint_summary = ""

    if complaint_found and "WEB_SIKAYET_KAYDI" in VALID_IDS:
        if not any(f.id == "WEB_SIKAYET_KAYDI" for f in base.flags):
            description = f"Şikayet kaydı ({complaint_source}): {complaint_summary}"[:120]
            base.flags.append(Flag(
                id="WEB_SIKAYET_KAYDI",
                category="web",
                evidence=complaint_entity,
                description=description,
            ))

    return base
