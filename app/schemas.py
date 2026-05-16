from pydantic import BaseModel


class Flag(BaseModel):
    flag_id: str
    title: str
    detail: str
    weight: float


class AnalysisResponse(BaseModel):
    risk_score: float          # 0.0 – 1.0
    risk_level: str            # "low" | "medium" | "high"
    flags: list[Flag]
    summary: str
