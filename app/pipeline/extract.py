import pathlib
from google import genai
from google.genai import types

from app.config import settings
from app.schemas import ExtractCikti

_PROMPT = (pathlib.Path(__file__).parent.parent / "prompts" / "extract.txt").read_text(encoding="utf-8")

_client = genai.Client(api_key=settings.gemini_api_key)
_cfg = types.GenerateContentConfig(
    response_mime_type="application/json",
    response_schema=ExtractCikti,
)


async def extract(metin: str | None, gorsel: bytes | None) -> ExtractCikti:
    """Stage 1: ham girdi → ExtractCikti. Kişisel veri işle-ve-at."""
    if gorsel is not None:
        contents = [
            types.Part.from_bytes(data=gorsel, mime_type="image/jpeg"),
            _PROMPT,
        ]
    else:
        contents = f"{_PROMPT}\n\nYazışma:\n{metin or ''}"

    response = await _client.aio.models.generate_content(
        model=settings.gemini_model,
        contents=contents,
        config=_cfg,
    )
    return ExtractCikti.model_validate_json(response.text)
