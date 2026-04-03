from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# class StrategyRunRequest(BaseModel):
#     code: str
#     rsiPeriod: int
#     maShortPeriod: int
#     maLongPeriod: int
#     volumePeriod: int
#     overboughtThreshold: float
#     oversoldThreshold: float
#     stopLossPercent: float
#     takeProfitPercent: float



# //     id: string;                // 唯一ID，可用 Date.now() 拼上随机数
# //   type: 'fundamental' | 'sentiment' | 'combined';
# //   queryParams: {
# //     stockCode?: string;       // 查询时输入的股票代码（可为空，代表全市场）
# //   };
# //   resultCount: number;
# //   createdAt: string;          // ISO 字符串
# //   data: StockRow[]; 
# //     stockName: string;
# //   stockCode: string;
# //   date: string;           // 格式 YYYY-MM-DD
# //   [key: string]: any;  

class TypeParam(BaseModel):
    paramType: str
    paramStrategy:str

class StockRow(BaseModel):
    stockName: str 
    stockCode: str 
    date: str 
    # key: str = Field(..., allow_inf_nan=False)

# class QueryParam(BaseModel):
#     stockCode: str 

class HistoryQueryItemResponse(BaseModel):
    id: str 
    type: str
    downloadURL: str
    resultCount: str 
    createAt: str 
    data:list[StockRow]


