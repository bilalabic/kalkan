from typing import Literal
from pydantic import BaseModel


class ExtractCikti(BaseModel):
    turns: list[str]
    urls: list[str]
    ibans: list[str]
    fiyat: str | None
    urun: str | None


class Flag(BaseModel):
    id: str
    kategori: str
    kanit: str
    aciklama: str


class ClassifyCikti(BaseModel):
    verdict: str
    flags: list[Flag]
    onerilen_aksiyonlar: list[str]


class LinkAnalizi(BaseModel):
    url: str
    durum: str
    gerekce: str


class AnalizSonucu(BaseModel):
    risk_seviyesi: Literal["dusuk", "orta", "yuksek"]
    risk_skoru: int                    # 0-100
    olasilik: float                    # 0.0-1.0
    verdict: str
    flags: list[Flag]
    link_analizi: list[LinkAnalizi]
    onerilen_aksiyonlar: list[str]
    sinyal_katkilari: dict[str, float]
