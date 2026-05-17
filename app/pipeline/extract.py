from __future__ import annotations

import asyncio
import pathlib

from google import genai
from google.genai import types

from app.config import settings
from app.schemas import ExtractOutput

_PROMPT = (pathlib.Path(__file__).parent.parent / "prompts" / "extract.txt").read_text(encoding="utf-8")

_client = genai.Client(api_key=settings.gemini_api_key)
_cfg = types.GenerateContentConfig(
    response_mime_type="application/json",
    response_schema=ExtractOutput,
)


async def extract(
    text: str | None,
    image: bytes | None,
    mime_type: str = "image/jpeg",
) -> ExtractOutput:
    if image is not None:
        contents = [types.Part.from_bytes(data=image, mime_type=mime_type), _PROMPT]
    else:
        contents = f"{_PROMPT}\n\nYazışma:\n{text or ''}"

    response = await _client.aio.models.generate_content(
        model=settings.gemini_model,
        contents=contents,
        config=_cfg,
    )
    return ExtractOutput.model_validate_json(response.text)


def _merge_extracts(extracts: list[ExtractOutput]) -> ExtractOutput:
    """Merge multiple ExtractOutputs from different images into one."""
    turns: list[str] = []
    seen_urls: set[str] = set()
    seen_ibans: set[str] = set()
    urls: list[str] = []
    ibans: list[str] = []

    for i, e in enumerate(extracts):
        if len(extracts) > 1 and e.turns:
            turns.append(f"[Görsel {i + 1}]")
        turns.extend(e.turns)
        for url in e.urls:
            if url not in seen_urls:
                seen_urls.add(url)
                urls.append(url)
        for iban in e.ibans:
            if iban not in seen_ibans:
                seen_ibans.add(iban)
                ibans.append(iban)

    price = next((e.price for e in extracts if e.price), None)
    product = next((e.product for e in extracts if e.product), None)
    return ExtractOutput(turns=turns, urls=urls, ibans=ibans, price=price, product=product)


async def extract_multi(
    text: str | None,
    images: list[tuple[bytes, str]],
) -> ExtractOutput:
    """Extract from up to 4 images (+ optional text) in parallel, then merge.

    Each element of `images` is a (bytes, mime_type) tuple.
    """
    if not images:
        return await extract(text=text, image=None)
    if len(images) == 1:
        data, mime = images[0]
        return await extract(text=text, image=data, mime_type=mime)

    tasks = [
        extract(text=text if i == 0 else None, image=data, mime_type=mime)
        for i, (data, mime) in enumerate(images)
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    valid = [r for r in results if isinstance(r, ExtractOutput)]
    if not valid:
        raise RuntimeError("Tüm görsel çıkarma işlemleri başarısız oldu.")
    return _merge_extracts(valid)
