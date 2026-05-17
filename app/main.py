from __future__ import annotations

import json as _json
import logging
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from app.pipeline.classify import classify, classify_stream
from app.pipeline.deterministic import run_deterministic
from app.pipeline.extract import extract_multi
from app.pipeline.fusion import fuse
from app.pipeline.verify import verify
from app.schemas import AnalysisResult

logger = logging.getLogger(__name__)

app = FastAPI(title="Kalkan", version="0.1.0", docs_url="/api/docs")


def _api_error_message(exc: Exception) -> str:
    """Return a user-friendly Turkish error message for known API errors."""
    msg = str(exc)
    if "429" in msg or "RESOURCE_EXHAUSTED" in msg or "quota" in msg.lower():
        return "Günlük API kotası doldu — lütfen birkaç dakika bekleyip tekrar deneyin."
    if "401" in msg or "API_KEY" in msg or "permission" in msg.lower():
        return "API anahtarı geçersiz veya eksik — lütfen yöneticiyle iletişime geçin."
    if "503" in msg or "unavailable" in msg.lower():
        return "Yapay zeka servisi geçici olarak kullanılamıyor — lütfen tekrar deneyin."
    return "Analiz servisi şu an yanıt vermiyor — lütfen tekrar deneyin."
app.mount("/static", StaticFiles(directory="static"), name="static")

_MAX_FILE_BYTES = 10 * 1024 * 1024
_MAX_FILES = 4
_ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp", "image/gif"}


@app.get("/", include_in_schema=False)
def root():
    return FileResponse("static/index.html")


@app.get("/health")
def health():
    return {"status": "ok"}


async def _read_images(files: list[UploadFile]) -> list[tuple[bytes, str]]:
    """Validate and read up to _MAX_FILES images; return (bytes, mime_type) tuples."""
    if len(files) > _MAX_FILES:
        raise HTTPException(
            status_code=422,
            detail=f"En fazla {_MAX_FILES} görsel yüklenebilir.",
        )
    result: list[tuple[bytes, str]] = []
    for f in files:
        content_type = f.content_type or ""
        if content_type not in _ALLOWED_MIME:
            raise HTTPException(
                status_code=415,
                detail=f"Desteklenmeyen dosya formatı: {content_type}. Lütfen JPEG, PNG veya WebP yükleyin.",
            )
        data = await f.read()
        if len(data) > _MAX_FILE_BYTES:
            raise HTTPException(status_code=413, detail="Dosya çok büyük. Maksimum boyut 10 MB.")
        result.append((data, content_type))
    return result


@app.post("/analyze", response_model=AnalysisResult)
async def analyze(
    gorsel: Annotated[list[UploadFile], File(description="Ekran görüntüsü (maks 4)")] = [],
    metin: Annotated[str | None, Form(description="Yazışma metni")] = None,
    deep: Annotated[bool, Form(description="Derin web kontrolü")] = False,
) -> AnalysisResult:
    if not gorsel and (not metin or not metin.strip()):
        raise HTTPException(
            status_code=422,
            detail="Lütfen bir ekran görüntüsü yükleyin veya yazışma metni girin.",
        )

    images = await _read_images(gorsel) if gorsel else []

    try:
        extracted = await extract_multi(text=metin, images=images)
    except Exception as exc:
        logger.error("extract stage failed: %s", exc)
        raise HTTPException(status_code=503, detail=_api_error_message(exc))

    try:
        det_flags, link_analysis = run_deterministic(extracted)
    except Exception as exc:
        logger.error("deterministic stage failed: %s", exc)
        det_flags, link_analysis = [], []

    try:
        classify_output = await classify(extracted, deep=deep)
    except Exception as exc:
        logger.error("classify stage failed: %s", exc)
        return _safe_response()

    try:
        verified = verify(classify_output, extracted)
    except Exception as exc:
        logger.error("verify stage failed: %s", exc)
        verified = classify_output

    det_ids = {f.id for f in det_flags}
    merged_flags = det_flags + [f for f in verified.flags if f.id not in det_ids]

    try:
        return fuse(
            flags=merged_flags,
            link_analysis=link_analysis,
            verdict=verified.verdict,
            recommended_actions=verified.recommended_actions,
        )
    except Exception as exc:
        logger.error("fusion stage failed: %s", exc)
        return _safe_response()


@app.post("/analyze/stream")
async def analyze_stream(
    gorsel: Annotated[list[UploadFile], File(description="Ekran görüntüsü (maks 4)")] = [],
    metin: Annotated[str | None, Form(description="Yazışma metni")] = None,
    deep: Annotated[bool, Form(description="Derin web kontrolü")] = False,
):
    """SSE endpoint — streams thinking tokens and stage events, then the final result."""
    if not gorsel and (not metin or not metin.strip()):
        raise HTTPException(
            status_code=422,
            detail="Lütfen bir ekran görüntüsü yükleyin veya yazışma metni girin.",
        )

    images = await _read_images(gorsel) if gorsel else []

    async def event_stream():
        def sse(data: dict) -> str:
            return f"data: {_json.dumps(data, ensure_ascii=False)}\n\n"

        label = f"{len(images)} görsel çıkarılıyor…" if len(images) > 1 else "Metin çıkarılıyor…"
        yield sse({"type": "stage", "label": label})
        try:
            extracted = await extract_multi(text=metin, images=images)
        except Exception as exc:
            logger.error("stream extract failed: %s", exc)
            yield sse({"type": "error", "message": _api_error_message(exc)})
            return

        yield sse({"type": "stage", "label": "Bağlantılar ve IBAN kontrol ediliyor…"})
        try:
            det_flags, link_analysis = run_deterministic(extracted)
        except Exception as exc:
            logger.error("stream deterministic failed: %s", exc)
            det_flags, link_analysis = [], []

        yield sse({"type": "stage", "label": "Sinyaller analiz ediliyor…"})
        classify_output = None
        classify_exc: Exception | None = None
        async for event_type, payload in classify_stream(extracted, deep=deep):
            if event_type == "thinking":
                yield sse({"type": "thinking", "text": payload})
            elif event_type == "error":
                classify_exc = payload
            else:
                classify_output = payload

        if classify_output is None:
            yield sse({"type": "error", "message": _api_error_message(classify_exc or Exception())})
            return

        yield sse({"type": "stage", "label": "Kanıtlar doğrulanıyor…"})
        try:
            verified = verify(classify_output, extracted)
        except Exception as exc:
            logger.error("stream verify failed: %s", exc)
            verified = classify_output

        yield sse({"type": "stage", "label": "Risk skoru hesaplanıyor…"})
        det_ids = {f.id for f in det_flags}
        merged_flags = det_flags + [f for f in verified.flags if f.id not in det_ids]

        try:
            analysis_result = fuse(
                flags=merged_flags,
                link_analysis=link_analysis,
                verdict=verified.verdict,
                recommended_actions=verified.recommended_actions,
            )
        except Exception as exc:
            logger.error("stream fusion failed: %s", exc)
            analysis_result = _safe_response()

        yield sse({"type": "result", "data": analysis_result.model_dump()})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _safe_response() -> AnalysisResult:
    return AnalysisResult(
        risk_level="orta",
        risk_score=50,
        probability=0.5,
        verdict="Analiz tamamlanamadı — lütfen manuel kontrol yapın.",
        flags=[],
        link_analysis=[],
        recommended_actions=[
            "Karşı tarafın kimliğini doğrulayın.",
            "Platform dışı ödeme yapmayın.",
            "Şüpheli durumlarda platformun destek hattını arayın.",
            "Gerekirse Tüketici Hakem Heyeti'ne başvurun.",
        ],
        signal_contributions={},
    )
