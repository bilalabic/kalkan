from __future__ import annotations

import logging

from rapidfuzz import fuzz

from app.schemas import ClassifyOutput, ExtractOutput, Flag

logger = logging.getLogger(__name__)

# Minimum fuzzy-match score (0–100) to keep a flag's evidence.
_MIN_SCORE = 60


def _match_score(evidence: str, corpus: str) -> float:
    if not evidence or not corpus:
        return 0.0
    return fuzz.partial_ratio(evidence.lower(), corpus.lower())


def verify(classify_output: ClassifyOutput, extracted: ExtractOutput) -> ClassifyOutput:
    """Stage 4: drop flags whose evidence string cannot be found in the original text."""
    # Use newline separator so turn-boundary spans don't merge into one word.
    corpus = "\n".join(extracted.turns)
    if extracted.urls:
        corpus += " " + " ".join(extracted.urls)
    if extracted.ibans:
        corpus += " " + " ".join(extracted.ibans)
    if extracted.price:
        corpus += " " + extracted.price
    if extracted.product:
        corpus += " " + extracted.product

    kept: list[Flag] = []
    for flag in classify_output.flags:
        score = _match_score(flag.evidence, corpus)
        if score >= _MIN_SCORE:
            kept.append(flag)
            logger.debug("verify: kept %s (score %.0f)", flag.id, score)
        else:
            logger.info(
                "verify: dropped %s — evidence not found (score %.0f < %d): '%s'",
                flag.id, score, _MIN_SCORE, flag.evidence[:80],
            )

    return ClassifyOutput(
        verdict=classify_output.verdict,
        flags=kept,
        recommended_actions=classify_output.recommended_actions,
    )
