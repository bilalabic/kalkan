"""Stage 5: log-odds risk fusion — no LLM.

Formula:  logit = B0 + Σ(weight_i * flag_i)
          P = sigmoid(logit),  score = round(P * 100)

Interaction rule: ODEME_PLATFORM_DISI ∧ LINK_SAHTE_KARGO → +1.5 bonus.
Override: any flag with severity="kritik" forces risk_level to "yuksek".
"""
from __future__ import annotations

import math

from app.schemas import AnalysisResult, Flag, LinkAnalysis
from app.taxonomy import FLAGS

B0: float = -1.4
INTERACTION_BONUS: float = 1.5


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def fuse(
    flags: list[Flag],
    link_analysis: list[LinkAnalysis],
    verdict: str,
    recommended_actions: list[str],
) -> AnalysisResult:
    flag_ids = {f.id for f in flags}
    signal_contributions: dict[str, float] = {}
    logit = B0

    for flag in flags:
        definition = FLAGS.get(flag.id)
        if definition is None:
            continue
        w = definition.log_odds_weight
        signal_contributions[flag.id] = w
        logit += w

    if "ODEME_PLATFORM_DISI" in flag_ids and "LINK_SAHTE_KARGO" in flag_ids:
        signal_contributions["ODEME_PLATFORM_DISI + LINK_SAHTE_KARGO"] = INTERACTION_BONUS
        logit += INTERACTION_BONUS

    probability = _sigmoid(logit)
    risk_score = round(probability * 100)

    if probability >= 0.7:
        risk_level = "yuksek"
    elif probability >= 0.4:
        risk_level = "orta"
    else:
        risk_level = "dusuk"

    if any(FLAGS.get(f.id) and FLAGS[f.id].severity == "kritik" for f in flags):
        risk_level = "yuksek"

    return AnalysisResult(
        risk_level=risk_level,
        risk_score=risk_score,
        probability=round(probability, 4),
        verdict=verdict,
        flags=flags,
        link_analysis=link_analysis,
        recommended_actions=recommended_actions,
        signal_contributions=signal_contributions,
    )
