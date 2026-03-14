# -*- coding: utf-8 -*-
"""Strategy endpoints."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from api.deps import get_database_manager
from api.v1.schemas.strategy import (
    StrategyRunRequest,
    StrategyRunResponse
)
from api.v1.schemas.common import ErrorResponse
from src.services.strategy_service import StrategyService
from src.storage import DatabaseManager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/run",
    response_model=StrategyRunResponse,
    responses={
        200: {"description": "回测执行完成"},
        500: {"description": "服务器错误", "model": ErrorResponse},
    },
    summary="触发回测",
    description="对历史分析记录进行回测评估",
)
def run_strategy(
    request: StrategyRunRequest,
    db_manager: DatabaseManager = Depends(get_database_manager),
) -> StrategyRunResponse:
    try:
        service = StrategyService(db_manager)
        stats = service.run_strategy(
            code=request.code,
            rsiPeriod=request.rsiPeriod,
            maShortPeriod=request.maShortPeriod,
            maLongPeriod=request.maLongPeriod,
            volumePeriod=request.volumePeriod,
            overboughtThreshold=request.overboughtThreshold,
            oversoldThreshold=request.oversoldThreshold,
            stopLossPercent=request.stopLossPercent,
            takeProfitPercent=request.takeProfitPercent,
        )
        return StrategyRunResponse(**stats)
    except Exception as exc:
        logger.error(f"回测执行失败: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "internal_error", "message": f"回测执行失败: {str(exc)}"},
        )

