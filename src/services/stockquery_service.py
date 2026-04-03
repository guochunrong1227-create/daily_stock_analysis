# -*- coding: utf-8 -*-
"""Query Stock orchestration service."""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, select

from src.config import get_config
from src.storage import DatabaseManager

logger = logging.getLogger(__name__)

import akshare as ak
from datetime import datetime, timezone
import pandas as pd
import os

#该类负责整理数据，并调用engine进行回测，不过目前直接在此函数中处理回测
class StockQueryService:
    """Service layer to run and query backtests."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or DatabaseManager.get_instance()

    def stock_query(
        self,
        type: str,
        strategy: str,
    ) -> Dict[str, Any]:
        today_str = date.today().strftime("%Y%m%d")
        download_dir = "./static/data"
        downloadURL = f"./data/fundamental_stock_data.csv"
        os.makedirs(download_dir,exist_ok=True)
        data = pd.DataFrame()
        title = ""
        if type == "fundamental":
            title = "基本面"
            file_path = './data/fundamental_stock_data.json'
            downloadURL = f"./data/fundamental_stock_data.csv"
            try:
                with open(file_path,'r',encoding='utf-8') as f:
                    data = json.load(f)
            except Exception:
                pass
            if len(data) == 0:
                stock_yjbb_em_df = ak.stock_yjbb_em(date="20251231")
                df_ranked = stock_yjbb_em_df.sort_values(
                    by=['净资产收益率','净利润-同比增长',  '每股收益','净利润-季度环比增长'],
                    ascending=False
                ).reset_index(drop=True)

                # logger.info(df_ranked.head(50)) #获取财务报表中排名前50的股票
                columns_map ={
                    '股票代码': 'stockCode',
                    '股票简称':'stockName',
                    '最新公告日期':'date'
                    }
            
                result = (df_ranked.loc[~df_ranked['股票代码'].str.startswith('8')]   # 先过滤
                    .head(50)[list(columns_map.keys())]
                    .rename(columns=columns_map)
                    .assign(date=lambda x: pd.to_datetime(x['date']).dt.strftime('%Y-%m-%d'))
                    # .to_dict('records')
                )
                data=result.to_dict('records').copy()
                # 将 data 存储到本地文件
                file_path = './data/fundamental_stock_data.json'  # 可根据需要修改路径
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                file_path = './static/data/fundamental_stock_data.csv'
                result.to_csv(file_path,index=False,encoding='utf-8')
                downloadURL = './data/fundamental_stock_data.csv'
        elif type=="sentiment":
            title = "人气榜"
            file_path = f'./data/sentiment_stock_data_{today_str}.json'
            try:
                with open(file_path,'r',encoding='utf-8') as f:
                    data = json.load(f)
            except Exception:
                pass
            if len(data)==0:
                comments_df = ak.stock_comment_em()
                #去掉当天涨停的股票：
                # comments_df = comments_df[~(comments_df['涨跌幅']>0.09)]
                # ['序号', '代码', '名称', '最新价', '涨跌幅', '换手率', '市盈率', '主力成本', '机构参与度', '综合得分', '上升', '目前排名', '关注指数', '交易日']
                # 1. 计算各列最大值（若最大值可能为0，可加条件保护）
                max_up = comments_df['上升'].max()
                max_attention = comments_df['关注指数'].max()
                # 避免除零（通常不会，但安全处理）
                if max_up == 0:
                    max_up = 1  # 或根据业务逻辑处理
                if max_attention == 0:
                    max_attention = 1

                # 2. 归一化
                comments_df['上升_norm'] = comments_df['上升'] / max_up
                comments_df['关注指数_norm'] = comments_df['关注指数'] / max_attention

                # 3. 计算加权总分（上升占60%，关注指数占40%）
                comments_df['新总分'] = comments_df['上升_norm'] * 0.65 + comments_df['关注指数_norm'] * 0.35
                
                # 4. 按新总分降序排序，重置索引
                df_sorted = comments_df.sort_values(by='新总分', ascending=False).reset_index(drop=True)
                
                columns_map ={
                    '代码': 'stockCode',
                    '名称':'stockName',
                    '交易日':'date'
                    }
            
                result = (df_sorted.loc[~df_sorted['代码'].str.startswith('8')]   # 先过滤
                    .head(50)[list(columns_map.keys())]
                    .rename(columns=columns_map)
                    .assign(date=lambda x: pd.to_datetime(x['date']).dt.strftime('%Y-%m-%d'))
                    .to_dict('records')
                )
                data=result.copy()
                # 将 data 存储到本地文件
                file_path = f'./data/sentiment_stock_data_{today_str}.json'  # 可根据需要修改路径
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
        elif type == "combined":
            # 'popularity' | 'rising' | 'breakout'
            if strategy == "popularity":
                title = "人气机构"
                file_path = f'./data/poplularity_stock_data_{today_str}.json'
                try:
                    with open(file_path,'r',encoding='utf-8') as f:
                        data = json.load(f)
                except Exception:
                    pass
                if len(data)==0:
                    comments_df = ak.stock_comment_em()
                    df_sorted = comments_df.sort_values(
                        by=['综合得分', '上升','关注指数','机构参与度'],
                        ascending=False
                    ).reset_index(drop=True)
                    columns_map ={
                        '代码': 'stockCode',
                        '名称':'stockName',
                        '交易日':'date'
                        }
                    result = (df_sorted.loc[~df_sorted['代码'].str.startswith('8')]   # 先过滤
                        .head(50)[list(columns_map.keys())]
                        .rename(columns=columns_map)
                        .assign(date=lambda x: pd.to_datetime(x['date']).dt.strftime('%Y-%m-%d'))
                        .to_dict('records')
                    )
                    data=result.copy()
                    # 将 data 存储到本地文件
                    file_path = f'./data/poplularity_stock_data_{today_str}.json'  # 可根据需要修改路径
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
            elif strategy == "rising":
                # 原始代码
                title = "人气收阳"
                file_path = f'./data/sentiment_rising_stock_data.json'  # 可根据需要修改路径
                with open(file_path,'r',encoding='utf-8') as f:
                    data = json.load(f)
            elif strategy == "breakout":
                title = "横盘突破"
                file_path = './data/breakout_stock_data.json'
                with open(file_path,'r',encoding='utf-8') as f:
                    data = json.load(f)
        else:
            pass
        now_utc = datetime.now(timezone.utc)
        iso_str = now_utc.isoformat()
        return{
            "id": f"{title}-{today_str}",
            "type": type,
            "downloadURL": downloadURL,
            # "queryParam": {
            #     "stockCode": "600519",
            # },
            "resultCount": f'{len(data)}',
            "createAt": iso_str,
            "data":data
            # "data": [{
            #     "stockName":"贵州茅台",
            #     "stockCode": "600519",
            #     "date":"2026/03/30"
            # }]
        }
    
    

# class StockRow(BaseModel):
#     stockName: str = Field(..., allow_inf_nan=False)
#     stockCode: str = Field(..., allow_inf_nan=False)
#     date: str = Field(..., allow_inf_nan=False)
#     # key: str = Field(..., allow_inf_nan=False)

# class HistoryQueryItemResponse(BaseModel):
#     id: str
#     type: str
#     queryParam: {
#         stockCode: str
#     }
#     resultCount: int
#     createAt: str
#     data:StockRow


