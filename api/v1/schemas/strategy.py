from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class StrategyRunRequest(BaseModel):
    code: str
    rsiPeriod: int
    maShortPeriod: int
    maLongPeriod: int
    volumePeriod: int
    overboughtThreshold: float
    oversoldThreshold: float
    stopLossPercent: float
    takeProfitPercent: float

class MetricsBase(BaseModel):
    totalReturn: float = Field(..., allow_inf_nan=False)
    winRate: float = Field(..., allow_inf_nan=False)
    maxDrawdown: float = Field(..., allow_inf_nan=False)
    sharpeRatio: float = Field(..., allow_inf_nan=False)

class StrategyRunResponse(BaseModel):
    code: str
    summary: str
    metrics: MetricsBase
    chartUrl: str


