from typing import Literal
from pydantic import BaseModel


class ExtractOutput(BaseModel):
    turns: list[str]
    urls: list[str]
    ibans: list[str]
    price: str | None
    product: str | None


class Flag(BaseModel):
    id: str
    category: str
    evidence: str
    description: str


class ClassifyOutput(BaseModel):
    verdict: str
    flags: list[Flag]
    recommended_actions: list[str]


class LinkAnalysis(BaseModel):
    url: str
    status: str
    reason: str


class AnalysisResult(BaseModel):
    risk_level: Literal["dusuk", "orta", "yuksek"]
    risk_score: int
    probability: float
    verdict: str
    flags: list[Flag]
    link_analysis: list[LinkAnalysis]
    recommended_actions: list[str]
    signal_contributions: dict[str, float]
