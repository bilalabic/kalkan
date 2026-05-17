"""Stage 3: LLM classification → ClassifyOutput (flag IDs from taxonomy).

Optional deep-check (deep=True): enables Google Search grounding and registers
check_domain as a function tool so the model can verify URLs and IBANs against
online complaint records. Falls back gracefully if the search call fails.
"""
from __future__ import annotations

import logging
import pathlib

from google import genai
from google.genai import types

from app.config import settings
from app.schemas import ClassifyOutput, ExtractOutput, Flag
from app.taxonomy import FLAGS, VALID_IDS
from app.tools.domain_check import check_domain

logger = logging.getLogger(__name__)

_PROMPT_PATH = pathlib.Path(__file__).parent.parent / "prompts" / "classify.txt"

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
    template = _PROMPT_PATH.read_text(encoding="utf-8")
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
        async for chunk in _client.aio.models.generate_content_stream(
            model=settings.gemini_model,
            contents=prompt,
            config=_cfg_standard,
        ):
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


async def _deep_check(extracted: ExtractOutput, base: ClassifyOutput) -> ClassifyOutput:
    """Search for online complaint records; appends WEB_SIKAYET_KAYDI if found."""
    entities = "\n".join(extracted.urls + extracted.ibans)
    prompt = (
        "Bu yazışmada geçen IBAN, telefon ve domain adlarını şikayetvar.com ve "
        "benzeri Türkçe şikayet sitelerinde kontrol et. "
        "Şikayet bulunan her öğe için 'WEB_SIKAYET_KAYDI' yaz ve kanıt kaynağını belirt.\n\n"
        f"Kontrol edilecek varlıklar:\n{entities}\n\n"
        "Yazışma:\n" + "\n".join(extracted.turns)
    )

    contents: list = [prompt]
    cfg_deep = types.GenerateContentConfig(tools=[_google_search_tool, _check_domain_tool])

    for _ in range(3):
        resp = await _client.aio.models.generate_content(
            model=settings.gemini_model,
            contents=contents,
            config=cfg_deep,
        )

        fn_calls = [
            p.function_call
            for c in (resp.candidates or [])
            for p in (c.content.parts or [])
            if p.function_call is not None
        ]

        if not fn_calls:
            text = resp.text or ""
            if "WEB_SIKAYET_KAYDI" in text and "WEB_SIKAYET_KAYDI" in VALID_IDS:
                search_snippet = next(
                    (ln for ln in text.splitlines() if "WEB_SIKAYET_KAYDI" in ln),
                    text[:200],
                )
                # Use first URL/IBAN as evidence — it's already in the extracted corpus
                # so verify stage won't drop this flag.
                evidence_entity = next(
                    iter(extracted.urls + extracted.ibans), search_snippet[:100]
                )
                if not any(f.id == "WEB_SIKAYET_KAYDI" for f in base.flags):
                    base.flags.append(Flag(
                        id="WEB_SIKAYET_KAYDI",
                        category="web",
                        evidence=evidence_entity,
                        description=f"İnternette şikayet kaydı tespit edildi: {search_snippet[:200]}",
                    ))
            break

        fn_responses = [
            types.Part.from_function_response(
                name="check_domain",
                response=check_domain((fn_call.args or {}).get("url", "")),
            )
            for fn_call in fn_calls
            if fn_call.name == "check_domain"
        ]

        if fn_responses:
            contents = [prompt, resp.candidates[0].content, *fn_responses]
        else:
            break

    return base
