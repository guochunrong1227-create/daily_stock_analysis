# -*- coding: utf-8 -*-
"""stockquery endpoints."""

from __future__ import annotations

import logging
from typing import Optional,Any

from fastapi import APIRouter, Depends, HTTPException, Query

from api.deps import get_database_manager
from api.v1.schemas.stockquery import (
    TypeParam,
    HistoryQueryItemResponse
)
from api.v1.schemas.common import ErrorResponse
from src.services.stockquery_service import StockQueryService
from src.storage import DatabaseManager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/run",
    response_model=HistoryQueryItemResponse,
    responses={
        200: {"description": "回测执行完成"},
        500: {"description": "服务器错误", "model": ErrorResponse},
    },
    summary="触发查询",
    description="获取基本面排名前30的股票",
)
def run_stockQuery(
    request: TypeParam,
    db_manager: DatabaseManager = Depends(get_database_manager),
    ) -> HistoryQueryItemResponse:

    # logger.info(f"victor Guo 2")

    try:
        service = StockQueryService(db_manager)
        stats = service.stock_query(
            type = request.paramType
        )
        return HistoryQueryItemResponse(**stats)
    except Exception as exc:
        logger.error(f"获取top50股票执行失败: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "internal_error", "message": f"获取top30股票执行失败: {str(exc)}"},
        )

