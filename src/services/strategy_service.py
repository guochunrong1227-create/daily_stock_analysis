# -*- coding: utf-8 -*-
"""Strategy orchestration service."""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, select

from src.config import get_config
from src.core.backtest_engine import OVERALL_SENTINEL_CODE, BacktestEngine, EvaluationConfig
from src.repositories.backtest_repo import BacktestRepository
from src.repositories.stock_repo import StockRepository
from src.storage import DatabaseManager

from data_provider import DataFetcherManager

logger = logging.getLogger(__name__)

from src.core.strategyEngine import StrategyEngine
import akquant as aq
# import akshare as ak
from akquant import Strategy
import akquant.plot as aqp
import imgkit
from PIL import Image


class MyStrategy(Strategy):
    def on_bar(self, bar):
        # 简单策略示例:
        # 当收盘价 > 开盘价 (阳线) -> 买入
        # 当收盘价 < 开盘价 (阴线) -> 卖出

        # 获取当前持仓
        current_pos = self.get_position(bar.symbol)

        if current_pos == 0 and bar.close > bar.open:
            self.buy(bar.symbol, 100)
            print(f"[{bar.timestamp_str}] Buy 100 at {bar.close:.2f}")

        elif current_pos > 0 and bar.close < bar.open:
            self.close_position(bar.symbol)
            print(f"[{bar.timestamp_str}] Sell 100 at {bar.close:.2f}")


#该类负责整理数据，并调用engine进行回测，不过目前直接在此函数中处理回测
class StrategyService:
    """Service layer to run and query backtests."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or DatabaseManager.get_instance()
    
    def run_strategy(
            self,
            code:str,
            rsiPeriod: int | None,
            maShortPeriod: int | None,
            maLongPeriod: int | None,
            volumePeriod: int | None,
            overboughtThreshold: float | None,
            oversoldThreshold: float | None,
            stopLossPercent: float | None,
            takeProfitPercent: float | None
    )-> Dict[str, Any]:
        multiStrategy = StrategyEngine()
        return (multiStrategy.run_strategy(code))

    def run_single_strategy(
        self,
        code: str,
        rsiPeriod: int | None,
        maShortPeriod: int | None,
        maLongPeriod: int | None,
        volumePeriod: int | None,
        overboughtThreshold: float | None,
        oversoldThreshold: float | None,
        stopLossPercent: float | None,
        takeProfitPercent: float | None
    ) -> Dict[str, Any]:
        config = get_config()
        # 1. 准备数据
        # 使用 akshare 获取 A 股历史数据 (需安装: pip install akshare)
        manager = DataFetcherManager()
        df = manager.get_daily_data(stock_code=code, start_date="20250901", end_date="20251231")
        df = df[0]
        # 运行回测
        result = aq.run_backtest(
            data=df,
            strategy=MyStrategy,
            symbol=code
        )
        logging.info(f"StrtegyService:\n{result.metrics_df}")

        # 生成完整的 HTML 报告
        result.report(
            title="完整策略报告",
            filename=f"./static/images/{code}_report.html",
            show=False  # 设为 True 以自动在浏览器中打开 (默认为 False)
        )
        
        aqp.plot_dashboard(
            result=result,
            title="策略仪表盘",
            show=False,
            filename=f"./static/images/{code}_dashboard.html"
        )
        # #  配置wkhtmltoimage路径（若未加入系统环境变量）
        # config = imgkit.config(wkhtmltoimage=r'C:\Program Files\wkhtmltopdf\bin\wkhtmltoimage.exe')

        # #定义imgkit配置
        # # options = {'format': 'png','quiet':''}
        # options = {
        #     'format': 'png',
        #     'width': 1200,  # 自定义宽度
        #     'quality': 80,  # 图像质量（0-100）
        #     'disable-smart-width': '',  # 禁用智能宽度调整
        #     'javascript-delay': 10000  # 等待JS加载（毫秒）
        # }
        # imgkit.from_file(
        #     filename=f"./static/images/{code}_report.html",
        #     output_path=f"./static/images/{code}_report.png",
        #     config=config,
        #     options=options)
        
        # img = Image.open(f"./static/images/{code}_report.png")
        # img_cropped = img.resize(size=([img.width/2,img.height/2]))
        # img_cropped.save("./static/images/{code}_report1.png")

        return{
            "code": code,
            "summary": f"127.0.0.1:8000/images/{code}_dashboard.html\n127.0.0.1:8000/images/{code}_report.html",
            "metrics":{
                "totalReturn":result.metrics_df.loc['total_profit','value'],
                "maxDrawdown":result.metrics_df.loc['max_drawdown','value'],
                "sharpeRatio":result.metrics_df.loc['sharpe_ratio','value'],
                "winRate":result.metrics_df.loc['win_rate','value']
            },
            "chartUrl": f"./images/demo.png",
            "bestStrategyDescription":"双均线",
        }
    #     // const responseData:StrategyResultResponse = {
    # //     'code': '000001',
    # //     'summary': 'report',
    # //     'metrics':{
    # //         'totalReturn': 50,
    # //         'maxDrawdown': 25,
    # //         'sharpeRatio': 30,
    # //         'winRate':55
    # //         },
    # //     'chartUrl':'./images/demo.png'
    # // }


