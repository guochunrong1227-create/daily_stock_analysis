#根据传入的数据来进行选择策略执行或者多个策略同时执行，比较最后的结果，告诉
#执行者，对于这个股票选择哪个策略比较好。

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, Iterable, List, Optional, Protocol, Sequence
import logging
import random
from src.config import get_config
import os

from data_provider import DataFetcherManager

# 特殊标记，用于表示汇总统计时的“全局”代码（例如汇总所有股票）
OVERALL_SENTINEL_CODE = "__overall__"

#该函数的主要逻辑：
#提供十种基本的策略：
# 策略一：双均线策略 (Dual Moving Average)
# 策略二：RSI 均值回归策略 (RSI Mean Reversion)
# 策略三：布林带策略 (Bollinger Bands)
# 策略四：唐奇安通道突破策略 (Donchian Channel Breakout)
# 策略五：布林带+RSI过滤策略 (Bollinger Bands with RSI Filter)
# 策略六：随机指标(KDJ)超买超卖策略 (Stochastic Oscillator)
# 策略七：成交量加权均线策略 (Volume Weighted Moving Average, VWAP)
# 策略八：海龟交易法则简化版 (Turtle Trading System Simplified)
# 策略九：基于斐波那契回撤的策略 (Fibonacci Retracement Strategy)
# 策略十：肯特纳通道突破策略 (Keltner Channel Breakout)

############################################################

# 策略一：双均线策略 (Dual Moving Average)¶
# 核心思想： 双均线策略利用两条不同周期的移动平均线（SMA）来判断市场趋势。 
# * 短期均线（如 5 日）：反应灵敏，紧跟价格波动。 * 长期均线（如 20 日）：反应迟钝，代表长期趋势。

# 交易信号： 
# * 金叉 (Golden Cross)：当短期均线 上穿 长期均线时，表明短期趋势走强，是 买入 信号。 
# * 死叉 (Death Cross)：当短期均线 下穿 长期均线时，表明短期趋势走弱，是 卖出 信号。


import akquant as aq
import pandas as pd
import numpy as np

from akquant import Strategy
import akquant.plot as aqp
import mplfinance as mpf
import matplotlib.pyplot as plt

from concurrent.futures import ThreadPoolExecutor, as_completed

from akquant import Bar, Instrument, Strategy
from akquant.live import LiveRunner  # 导入实盘运行器
import time


class DualSMAStrategy(aq.Strategy):
    def __init__(self, short_window=5, long_window=20):
        self.sma_short = aq.SMA(short_window)
        self.sma_long = aq.SMA(long_window)

    def on_bar(self, bar: aq.Bar):
        short_val = self.sma_short.update(bar.close)
        long_val = self.sma_long.update(bar.close)

        if short_val is None or long_val is None:
            return

        position = self.get_position(bar.symbol)

        if short_val > long_val and position == 0:
            self.buy(bar.symbol, 1000)

        elif short_val < long_val and position > 0:
            self.sell(bar.symbol, 1000)

# 策略二：RSI 均值回归策略 (RSI Mean Reversion)¶
# 核心思想： RSI (相对强弱指标) 是一种动量指标，数值范围在 0 到 100 之间，
# 用于衡量近期价格变化的幅度。 * 均值回归 (Mean Reversion)：
# 该策略假设价格不会一直涨或一直跌，过度偏离后会回归正常水平。 
# * 超卖 (Oversold)：RSI 低于某个阈值（如 30），意味着近期跌幅过大，可能反弹 -> 买入。 
# * 超买 (Overbought)：RSI 高于某个阈值（如 70），意味着近期涨幅过大，可能回调 -> 卖出。

class RSIStrategy(aq.Strategy):
    def __init__(self, period=14, buy_threshold=30, sell_threshold=70):
        self.period = period
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold
        self.set_history_depth(period + 20)

    def calculate_rsi(self, prices: pd.Series) -> pd.Series:
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def on_bar(self, bar: aq.Bar):
        history = self.get_history_df(self.period + 20, bar.symbol)

        if len(history) < self.period + 1:
            return

        rsi_series = self.calculate_rsi(history['close'])
        current_rsi = rsi_series.iloc[-1]

        if np.isnan(current_rsi):
            return

        position = self.get_position(bar.symbol)

        if current_rsi < self.buy_threshold and position == 0:
            self.buy(bar.symbol, 1000)

        elif current_rsi > self.sell_threshold and position > 0:
            self.sell(bar.symbol, 1000)

# 策略三：布林带策略 (Bollinger Bands)
# 核心思想： 布林带由三条轨道线组成： 
# * 中轨：N 日移动平均线。 
# * 上轨：中轨 + K 倍标准差。 
# * 下轨：中轨 - K 倍标准差。

# 根据统计学原理，价格有很大（如 95%）的概率落在上下轨之间。 
# * 当价格跌破下轨时，通常被视为非理性的超卖状态，价格可能会回归中轨 -> 买入。 
# * 当价格突破上轨时，通常被视为非理性的超买状态，价格可能会回调 -> 卖出。

class BollingerStrategy(aq.Strategy):
    def __init__(self, window=20, num_std=2):
        self.window = window
        self.num_std = num_std
        self.set_history_depth(window + 5)

    def on_bar(self, bar: aq.Bar):
        history = self.get_history_df(self.window, bar.symbol)
        if len(history) < self.window:
            return

        close_prices = history['close']
        ma = close_prices.mean()
        std = close_prices.std()
        upper_band = ma + self.num_std * std
        lower_band = ma - self.num_std * std

        position = self.get_position(bar.symbol)
        current_price = bar.close

        if current_price < lower_band and position == 0:
            self.buy(bar.symbol, 1000)

        elif current_price > upper_band and position > 0:
            self.sell(bar.symbol, 1000)

# 策略四：唐奇安通道突破策略 (Donchian Channel Breakout)
# 核心思想：唐奇安通道由过去N日的最高价和最低价构成。
# * 当价格突破过去N日最高价时，视为向上突破，可能开启上升趋势 -> 买入。
# * 当价格跌破过去N日最低价时，视为向下突破，可能开启下降趋势 -> 卖出（平多）。
# 此策略是海龟交易法则的基础，通常结合ATR动态调整仓位，这里简化处理。

class DonchianBreakoutStrategy(aq.Strategy):
    def __init__(self, window=20):
        self.window = window
        self.set_history_depth(window + 5)

    def on_bar(self, bar: aq.Bar):
        history = self.get_history_df(self.window, bar.symbol)
        if len(history) < self.window:
            return

        # 计算过去N日的最高价和最低价
        high_prices = history['high']
        low_prices = history['low']
        channel_high = high_prices.max()
        channel_low = low_prices.min()

        position = self.get_position(bar.symbol)
        current_price = bar.close

        # 价格突破上轨且无持仓 -> 买入
        if current_price > channel_high and position == 0:
            self.buy(bar.symbol, 1000)

        # 价格跌破下轨且有持仓 -> 卖出
        elif current_price < channel_low and position > 0:
            self.sell(bar.symbol, 1000)

# 策略五：布林带+RSI过滤策略 (Bollinger Bands with RSI Filter)
# 核心思想：结合布林带的均值回归特性和RSI的动量过滤，减少假突破。
# * 布林带下轨提供潜在买入区，但仅当RSI也处于超卖（<30）时确认，提高信号可靠性。
# * 布林带上轨提供潜在卖出区，但仅当RSI处于超买（>70）时确认，避免在强趋势中过早反向开仓。
# * 当持仓时，若价格回归中轨或RSI脱离极端区，可考虑平仓（此处简化：触及上/下轨反向信号平仓）。

class BollingerRSIStrategy(aq.Strategy):
    def __init__(self, window=20, num_std=2, rsi_period=14, oversold=30, overbought=70):
        self.window = window
        self.num_std = num_std
        self.rsi_period = rsi_period
        self.oversold = oversold
        self.overbought = overbought
        self.set_history_depth(max(window, rsi_period) + 10)

    def on_bar(self, bar: aq.Bar):
        # 获取足够的历史数据
        history = self.get_history_df(max(self.window, self.rsi_period) + 5, bar.symbol)
        if len(history) < max(self.window, self.rsi_period) + 1:
            return

        close_prices = history['close']
        # 布林带计算
        ma = close_prices[-self.window:].mean()
        std = close_prices[-self.window:].std()
        upper_band = ma + self.num_std * std
        lower_band = ma - self.num_std * std

        # RSI计算
        deltas = close_prices.diff().values[1:]  # 价格差分
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        avg_gain = gains[-self.rsi_period:].mean()
        avg_loss = losses[-self.rsi_period:].mean()
        if avg_loss == 0:
            rsi = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - 100 / (1 + rs)

        position = self.get_position(bar.symbol)
        current_price = bar.close

        # 买入信号：价格低于下轨且RSI超卖，且无持仓
        if current_price < lower_band and rsi < self.oversold and position == 0:
            self.buy(bar.symbol, 1000)

        # 卖出信号：价格高于上轨且RSI超买，且有持仓
        elif current_price > upper_band and rsi > self.overbought and position > 0:
            self.sell(bar.symbol, 1000)

# 策略六：随机指标(KDJ)超买超卖策略 (Stochastic Oscillator)
# 核心思想：KDJ反映当前价格在近期波动区间内的相对位置，常用于识别超买超卖。
# * 当K线从下方上穿D线，且K<20（超卖区），视为买入信号。
# * 当K线从上方下穿D线，且K>80（超买区），视为卖出信号。
# * 此处使用经典KDJ（9,3,3）简化计算。

class KDJStrategy(aq.Strategy):
    def __init__(self, n=9, m1=3, m2=3, oversold=20, overbought=80):
        self.n = n
        self.m1 = m1
        self.m2 = m2
        self.oversold = oversold
        self.overbought = overbought
        self.set_history_depth(n + m1 + m2 + 10)

    def on_bar(self, bar: aq.Bar):
        history = self.get_history_df(self.n + self.m1 + self.m2 + 5, bar.symbol)
        if len(history) < self.n + self.m1 + self.m2:
            return

        # 取最近n根K线的最高价和最低价
        high_prices = history['high']
        low_prices = history['low']
        close_prices = history['close']

        # 计算未成熟随机值RSV
        highest_high = high_prices.rolling(window=self.n).max()
        lowest_low = low_prices.rolling(window=self.n).min()
        rsv = 100 * (close_prices - lowest_low) / (highest_high - lowest_low)
        rsv = rsv.fillna(50)  # 避免除零

        # 计算K值（RSV的M1日移动平均）
        k = rsv.rolling(window=self.m1).mean()
        # 计算D值（K的M2日移动平均）
        d = k.rolling(window=self.m2).mean()

        current_k = k.iloc[-1]
        current_d = d.iloc[-1]
        prev_k = k.iloc[-2]
        prev_d = d.iloc[-2]

        position = self.get_position(bar.symbol)

        # 买入信号：K上穿D且K<20
        if current_k > current_d and prev_k <= prev_d and current_k < self.oversold and position == 0:
            self.buy(bar.symbol, 1000)

        # 卖出信号：K下穿D且K>80
        elif current_k < current_d and prev_k >= prev_d and current_k > self.overbought and position > 0:
            self.sell(bar.symbol, 1000)

# 策略七：成交量加权均线策略 (Volume Weighted Moving Average, VWAP)
# 核心思想：VWAP是考虑了成交量的平均价格，反映市场的真实成交成本。
# * 当价格从下方突破VWAP时，表明买方力量增强，可能开启上涨 -> 买入。
# * 当价格从上方跌破VWAP时，表明卖方力量增强，可能开启下跌 -> 卖出。
# * 使用当日VWAP作为动态支撑/阻力，此处基于历史数据计算（通常用于日内，但可用于日线）。

class VWAPStrategy(aq.Strategy):
    def __init__(self, window=20):
        self.window = window
        self.set_history_depth(window + 5)

    def on_bar(self, bar: aq.Bar):
        history = self.get_history_df(self.window, bar.symbol)
        if len(history) < self.window:
            return

        # 计算VWAP：sum(价格 * 成交量) / sum(成交量)
        typical_price = (history['high'] + history['low'] + history['close']) / 3
        vwap = (typical_price * history['volume']).sum() / history['volume'].sum()

        position = self.get_position(bar.symbol)
        current_price = bar.close

        # 获取前一日价格（用于判断穿越）
        prev_history = self.get_history_df(self.window + 1, bar.symbol)
        if len(prev_history) < self.window + 1:
            return
        prev_close = prev_history['close'].iloc[-2]

        # 价格上穿VWAP
        if current_price > vwap and prev_close <= vwap and position == 0:
            self.buy(bar.symbol, 1000)

        # 价格下穿VWAP
        elif current_price < vwap and prev_close >= vwap and position > 0:
            self.sell(bar.symbol, 1000)

# 策略八：海龟交易法则简化版 (Turtle Trading System Simplified)
# 核心思想：基于唐奇安通道突破进行趋势跟踪，并结合ATR动态管理仓位和止损。
# * 入场：价格突破过去20日最高价做多，突破过去10日最低价做空（反向）。
# * 止损：以2倍ATR作为跟踪止损，价格回撤超过2倍ATR则平仓。
# * 此版本只做多，且简化止损逻辑，使用固定ATR倍数止损。

class TurtleStrategy(aq.Strategy):
    def __init__(self, entry_window=20, stop_window=10, atr_period=14, atr_multiplier=2):
        self.entry_window = entry_window
        self.stop_window = stop_window
        self.atr_period = atr_period
        self.atr_multiplier = atr_multiplier
        self.set_history_depth(max(entry_window, stop_window, atr_period) + 10)
        self.stop_price = None  # 记录当前持仓的止损价

    def on_bar(self, bar: aq.Bar):
        history = self.get_history_df(self.atr_period + 5, bar.symbol)
        if len(history) < self.atr_period:
            return

        # 计算ATR（平均真实波幅）
        high, low, close = history['high'], history['low'], history['close']
        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=self.atr_period).mean().iloc[-1]

        position = self.get_position(bar.symbol)
        current_price = bar.close

        # 入场逻辑
        if position == 0:
            # 计算突破价格
            entry_high = history['high'].iloc[-self.entry_window:].max()
            if current_price > entry_high:
                self.buy(bar.symbol, 1000)
                # 设置初始止损价：入场价 - atr_multiplier * ATR
                self.stop_price = current_price - self.atr_multiplier * atr
        else:
            # 持仓中：更新止损（此处使用移动止损：以当前K线最高价减去倍数ATR，确保不降低）
            new_stop = bar.high - self.atr_multiplier * atr
            if new_stop > self.stop_price:
                self.stop_price = new_stop

            # 止损检查
            if current_price <= self.stop_price:
                self.sell(bar.symbol, 1000)
                self.stop_price = None

# 策略九：基于斐波那契回撤的策略 (Fibonacci Retracement Strategy)
# 核心思想：在上升趋势中，价格往往会在回调至关键斐波那契水平（如0.382、0.5、0.618）后获得支撑并恢复上涨。
# 本策略简化实现：
# * 计算过去N日内的最高价（HH）和最低价（LL），作为近期波动的基准区间。
# * 斐波那契支撑位 = HH - fib_level * (HH - LL)，通常取0.618作为回调买入区域。
# * 当价格从高位下跌后，首次收盘价站上该支撑位，视为回调结束信号 -> 买入。
# * 止损：若价格再次跌破该支撑位，则平仓。
# 注意：本策略仅做多，且需确保有足够的价格波动以产生有效区间。

class FibonacciRetracementStrategy(aq.Strategy):
    def __init__(self, window=20, fib_level=0.618):
        self.window = window
        self.fib_level = fib_level
        self.set_history_depth(window + 5)  # 多取一些数据以便计算前一日收盘

    def on_bar(self, bar: aq.Bar):
        # 获取历史数据（需包含当前及前一周期）
        history = self.get_history_df(self.window + 1, bar.symbol)
        if len(history) < self.window + 1:
            return

        high_prices = history['high']
        low_prices = history['low']
        close_prices = history['close']

        # 计算过去window日的最高价和最低价
        hh = high_prices.iloc[-self.window:].max()
        ll = low_prices.iloc[-self.window:].min()
        diff = hh - ll
        if diff <= 0:
            return  # 波动范围为零，无意义

        # 计算斐波那契支撑位
        support = hh - self.fib_level * diff

        current_close = close_prices.iloc[-1]
        prev_close = close_prices.iloc[-2]
        position = self.get_position(bar.symbol)

        # 买入信号：前一日收盘在支撑之下，今日收盘站上支撑（确认回调结束）
        if prev_close < support and current_close > support and position == 0:
            self.buy(bar.symbol, 1000)

        # 止损信号：持仓后价格再次跌破支撑
        elif position > 0 and current_close < support:
            self.sell(bar.symbol, 1000)

# 策略十：肯特纳通道突破策略 (Keltner Channel Breakout)
# 核心思想：肯特纳通道基于EMA和ATR构建，反映价格波动范围。
# * 中轨：N日EMA。
# * 上轨：中轨 + K * ATR。
# * 下轨：中轨 - K * ATR。
# 本策略采用趋势跟踪方式：
# * 当价格收盘突破上轨时，视为强势上涨信号 -> 买入。
# * 当价格收盘跌破下轨时，视为弱势下跌信号 -> 卖出（平多）。
# 该策略在趋势行情中表现较好，震荡市中可能产生反复信号。

class KeltnerChannelStrategy(aq.Strategy):
    def __init__(self, period=20, multiplier=2, ema_span=20):
        self.period = period          # ATR计算周期
        self.multiplier = multiplier  # 通道倍数
        self.ema_span = ema_span      # EMA周期
        self.set_history_depth(max(period, ema_span) + 10)

    def on_bar(self, bar: aq.Bar):
        # 获取足够历史数据计算EMA和ATR
        history = self.get_history_df(self.period + 5, bar.symbol)
        if len(history) < self.period + 1:
            return

        # 计算EMA
        close = history['close']
        ema = close.ewm(span=self.ema_span, adjust=False).mean()

        # 计算ATR（平均真实波幅）
        high, low, close_ = history['high'], history['low'], history['close']
        tr1 = high - low
        tr2 = (high - close_.shift()).abs()
        tr3 = (low - close_.shift()).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=self.period).mean()

        # 当前通道值
        current_ema = ema.iloc[-1]
        current_atr = atr.iloc[-1]
        upper = current_ema + self.multiplier * current_atr
        lower = current_ema - self.multiplier * current_atr

        current_price = bar.close
        position = self.get_position(bar.symbol)

        # 价格突破上轨，开多
        if current_price > upper and position == 0:
            self.buy(bar.symbol, 1000)

        # 价格跌破下轨，平多
        elif current_price < lower and position > 0:
            self.sell(bar.symbol, 1000)

# 策略十一：CDMA趋势检测策略 (Change Detection by Moving Average)
# 核心思想：CDMA通过移动平均线检测价格变化趋势，识别趋势转折点。
# * 计算短期和长期移动平均线的变化率，检测趋势强度变化。
# * 当短期MA变化率上穿长期MA变化率时，表明趋势加速 -> 买入。
# * 当短期MA变化率下穿长期MA变化率时，表明趋势减速 -> 卖出。
# * 结合MACD指标确认背离现象，提高信号可靠性。

class CDMAStrategy(aq.Strategy):
    def __init__(self, short_window=5, long_window=20, macd_fast=12, macd_slow=26, macd_signal=9):
        self.short_window = short_window
        self.long_window = long_window
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal
        self.set_history_depth(max(long_window, macd_slow) + macd_signal + 30)

    def on_bar(self, bar: aq.Bar):
        # 获取足够的历史数据
        history = self.get_history_df(self.long_window + self.macd_slow + 30, bar.symbol)
        if len(history) < self.long_window + self.macd_slow:
            return

        close_prices = history['close']

        # 1. 计算移动平均线
        short_ma = close_prices.rolling(window=self.short_window).mean()
        long_ma = close_prices.rolling(window=self.long_window).mean()

        # 2. 计算MA变化率（价格变化趋势）
        short_ma_roc = short_ma.pct_change() * 100  # 短期MA变化率
        long_ma_roc = long_ma.pct_change() * 100    # 长期MA变化率

        # 3. 计算MACD指标（用于背离确认）
        ema_fast = close_prices.ewm(span=self.macd_fast, adjust=False).mean()
        ema_slow = close_prices.ewm(span=self.macd_slow, adjust=False).mean()
        dif = ema_fast - ema_slow
        dea = dif.ewm(span=self.macd_signal, adjust=False).mean()
        macd_hist = dif - dea  # MACD柱状线

        # 当前值
        current_short_roc = short_ma_roc.iloc[-1]
        current_long_roc = long_ma_roc.iloc[-1]
        current_dif = dif.iloc[-1]
        current_hist = macd_hist.iloc[-1]

        # 前一期值（用于判断穿越）
        prev_short_roc = short_ma_roc.iloc[-2]
        prev_long_roc = long_ma_roc.iloc[-2]
        prev_dif = dif.iloc[-2]
        prev_hist = macd_hist.iloc[-2]

        # 处理NaN值
        if any(pd.isna([current_short_roc, current_long_roc, current_dif, current_hist])):
            return

        position = self.get_position(bar.symbol)

        # 买入信号条件：
        # 1. 短期MA变化率上穿长期MA变化率（趋势加速）
        # 2. MACD柱状线由负转正或DIF上穿DEA（动能确认）
        # 3. 价格处于上升趋势（可选：收盘价在长期MA之上）
        buy_signal = (
            current_short_roc > current_long_roc and 
            prev_short_roc <= prev_long_roc and
            current_hist > 0 and 
            prev_hist <= 0 and
            close_prices.iloc[-1] > long_ma.iloc[-1]  # 价格在长期均线上方
        )

        # 卖出信号条件：
        # 1. 短期MA变化率下穿长期MA变化率（趋势减速）
        # 2. MACD柱状线由正转负或DIF下穿DEA（动能衰竭）
        # 3. 价格处于下降趋势（可选：收盘价在长期MA之下）
        sell_signal = (
            current_short_roc < current_long_roc and 
            prev_short_roc >= prev_long_roc and
            current_hist < 0 and 
            prev_hist >= 0 and
            close_prices.iloc[-1] < long_ma.iloc[-1]  # 价格在长期均线下方
        )

        # 执行交易
        if buy_signal and position == 0:
            self.buy(bar.symbol, 1000)

        elif sell_signal and position > 0:
            self.sell(bar.symbol, 1000)

# 策略十二：尾盘买入次日冲高卖出 (Tail Buy & Next Day Sell)
# 核心思想：
# 在每日尾盘（如14:55）筛选出当日温和上涨、成交量放大且站上20日均线的股票买入，
# 次日设定止盈（+3%）、止损（-2%）或尾盘强制卖出，以获取短线冲高收益。
#
# 选股逻辑（同时满足）：
# 1. 当前价格 > 20日均线（趋势向上）
# 2. 当日成交量 > 1.5倍5日均量（放量）
# 3. 当日涨幅（相对于昨日收盘）在 1% ~ 5% 之间（避免追高和弱势）
#
# 卖出逻辑：
# 1. 次日股价涨幅达到 +3% 时止盈卖出
# 2. 次日股价跌幅达到 -2% 时止损卖出
# 3. 次日14:50后仍未卖出则强制平仓（避免隔夜风险）

import datetime

class TailBuyStrategy(aq.Strategy):
    def __init__(self,
                 buy_time="14:55",           # 尾盘买入时间点（之后）
                 sell_time="14:50",           # 次日强制卖出时间点
                 profit_target=0.03,          # 止盈目标 +3%
                 stop_loss=-0.02,              # 止损线 -2%
                 volume_ratio=1.5,             # 成交量相对于5日均量的倍数
                 ma_period=20,                  # 均线周期
                 min_change=0.01,               # 最小涨幅 1%
                 max_change=0.05):               # 最大涨幅 5%
        """
        初始化策略参数
        """
        self.buy_time = buy_time
        self.sell_time = sell_time
        self.profit_target = profit_target
        self.stop_loss = stop_loss
        self.volume_ratio = volume_ratio
        self.ma_period = ma_period
        self.min_change = min_change
        self.max_change = max_change

        # 状态变量
        self.positions = {}          # 当前持仓：{symbol: {'buy_price':价格, 'buy_date':日期}}
        self.bought_today = set()     # 当天已买入的股票（避免重复买入）
        self.daily_data = {}          # 当日累计OHLCV数据：{symbol: {'open':, 'high':, 'low':, 'volume':, 'date':}}

        # 设置历史数据深度（确保计算均线等指标时有足够数据）
        # 如果框架不支持 set_history_depth，可注释掉下一行
        self.set_history_depth(max(ma_period, 5) + 10)

    def _get_bar_datetime(self, bar):
        """
        从Bar对象中安全获取当前时间和日期（兼容不同属性名，包括timestamp）
        """
        # 1. 优先使用timestamp（Unix纳秒整数）
        if hasattr(bar, 'timestamp') and bar.timestamp is not None:
            ts_ns = bar.timestamp
            # 将纳秒转换为秒（浮点数），然后转为datetime
            dt = datetime.datetime.fromtimestamp(ts_ns / 1e9)
            return dt.time(), dt.date()

        # 2. 检查常见的datetime属性
        if hasattr(bar, 'datetime') and bar.datetime is not None:
            dt = bar.datetime
            return dt.time(), dt.date()

        # 3. 检查dt属性
        if hasattr(bar, 'dt') and bar.dt is not None:
            dt = bar.dt
            return dt.time(), dt.date()

        # 4. 检查分开的time和date属性
        if hasattr(bar, 'time') and hasattr(bar, 'date'):
            # 如果time是字符串，尝试解析
            if isinstance(bar.time, str):
                t = datetime.datetime.strptime(bar.time, "%H:%M:%S").time()
            else:
                t = bar.time
            d = bar.date
            return t, d

        # 如果以上都不满足，抛出异常
        raise AttributeError("无法从Bar对象中提取时间和日期")

    def on_bar(self, bar: aq.Bar):
        """
        每个新的K线到达时调用
        """
        symbol = bar.symbol
        current_time, current_date = self._get_bar_datetime(bar)

        # ----- 1. 更新当日累计数据 -----
        if symbol not in self.daily_data or self.daily_data[symbol]['date'] != current_date:
            # 新的一天，重置该股票的当日数据
            self.daily_data[symbol] = {
                'open': bar.open,
                'high': bar.high,
                'low': bar.low,
                'volume': bar.volume,
                'date': current_date
            }
            # 如果之前该股票当天被标记为已买入，移除标记（因为日期已变）
            if symbol in self.bought_today:
                self.bought_today.remove(symbol)
        else:
            # 更新当天最高、最低和累计成交量
            self.daily_data[symbol]['high'] = max(self.daily_data[symbol]['high'], bar.high)
            self.daily_data[symbol]['low'] = min(self.daily_data[symbol]['low'], bar.low)
            self.daily_data[symbol]['volume'] += bar.volume

        # ----- 2. 尾盘买入逻辑 -----
        if self._is_buy_time(current_time):
            # 当天已买入该股票则跳过
            if symbol in self.bought_today:
                return

            # 获取日线历史数据（用于计算均线和均量）
            # 假设 get_history_df 支持 frequency='1d' 参数获取日线数据
            daily_history = self.get_history_df(self.ma_period + 5, symbol, frequency='1d')
            if len(daily_history) < self.ma_period + 1:
                return

            # 计算昨日收盘价
            prev_close = daily_history['close'].iloc[-1]
            current_price = bar.close
            change = (current_price / prev_close - 1)

            # 计算20日均线（使用最近20日收盘价，不含今日）
            ma = daily_history['close'].rolling(window=self.ma_period).mean().iloc[-1]

            # 计算5日均量（使用最近5日成交量，不含今日）
            volume_ma5 = daily_history['volume'].rolling(window=5).mean().iloc[-1]
            today_volume = self.daily_data[symbol]['volume']

            # 选股条件
            condition1 = current_price > ma                     # 站上20日均线
            condition2 = today_volume > self.volume_ratio * volume_ma5  # 放量
            condition3 = self.min_change <= change <= self.max_change    # 涨幅适中

            if condition1 and condition2 and condition3:
                # 买入固定股数（此处为1000股，可根据资金调整）
                self.buy(symbol, 1000)
                self.positions[symbol] = {
                    'buy_price': current_price,
                    'buy_date': current_date
                }
                self.bought_today.add(symbol)

        # ----- 3. 次日卖出逻辑（针对持仓股票） -----
        if symbol in self.positions:
            pos = self.positions[symbol]
            buy_date = pos['buy_date']

            # 买入当天不卖出（必须隔夜）
            if current_date == buy_date:
                return

            # 计算当前盈亏比例
            pnl = (bar.close / pos['buy_price'] - 1)

            sell_signal = False
            # 止盈
            if pnl >= self.profit_target:
                sell_signal = True
            # 止损
            elif pnl <= self.stop_loss:
                sell_signal = True
            # 尾盘强制卖出（时间到达设定点且未触发止盈止损）
            elif current_time >= datetime.datetime.strptime(self.sell_time, "%H:%M").time() and current_time < datetime.time(15,0):
                sell_signal = True

            if sell_signal:
                self.sell(symbol, 1000)   # 平仓
                del self.positions[symbol]

    def _is_buy_time(self, t):
        """
        判断当前时间是否在买入窗口（买入时间点到收盘前）
        """
        buy_t = datetime.datetime.strptime(self.buy_time, "%H:%M").time()
        return t >= buy_t and t < datetime.time(15, 0)
# 策略说明

# 选股逻辑
# 价格站上20日均线：确保股票处于短期上升趋势。
# 成交量放大至5日均量的1.5倍以上：反映资金活跃，可能为主力抢筹。
# 当日涨幅在1%~5%之间：避免追高（涨幅过大可能回调）和弱势股（涨幅过小缺乏动能）。
# 以上条件同时满足时，在尾盘（如14:55后）以收盘价附近买入。
# 卖出逻辑
# 止盈+3%：锁定利润，符合短线冲高预期。
# 止损-2%：控制单笔亏损。
# 次日尾盘强制卖出：无论盈亏，在14:50后平仓，避免持仓过夜带来不确定性。
# 三个条件任意触发即卖出。
# 代码实现要点
# 使用daily_data字典实时累计当日OHLCV数据，近似构造日线用于选股。
# 通过get_history_df(frequency='1d')获取日线历史数据（需框架支持）。
# 利用bought_today和positions分别管理当日买入标记和持仓状态，避免重复交易。
# 卖出逻辑仅在次日检查，确保持股周期仅为1天。

# #策略十三：机器学习策略
# from sklearn.linear_model import LogisticRegression
# from sklearn.preprocessing import StandardScaler
# from sklearn.pipeline import Pipeline

# from akquant import Strategy, ExecutionMode, run_backtest
# from akquant.ml import SklearnAdapter

# from akquant.ml import PyTorchAdapter
# import torch.nn as nn
# import torch.optim as optim

# # 定义网络
# class SimpleNet(nn.Module):
#     def __init__(self):
#         super().__init__()
#         self.fc = nn.Sequential(
#             nn.Linear(10, 32),
#             nn.ReLU(),
#             nn.Linear(32, 1),
#             nn.Sigmoid()
#         )

#     def forward(self, x):
#         return self.fc(x)

# class WalkForwardStrategy(Strategy):
#     """
#     演示策略：使用逻辑回归预测涨跌 (集成 Pipeline 预处理)
#     """

#     def __init__(self):
#         # 1. 初始化模型 (使用 Pipeline 封装预处理和模型)
#         # StandardScaler: 确保使用训练集统计量进行标准化，防止数据泄露
#         pipeline = Pipeline([
#             ('scaler', StandardScaler()),
#             ('model', LogisticRegression())
#         ])


#         # 在策略中使用
#         self.model = PyTorchAdapter(
#             network=SimpleNet(),
#             criterion=nn.BCELoss(),
#             optimizer_cls=optim.Adam,
#             lr=0.001,
#             epochs=20,
#             batch_size=64,
#             device='CPU'  # 支持 GPU 加速
#         )

#         # self.model = SklearnAdapter(pipeline)

#         # 2. 配置 Walk-forward Validation
#         # 框架会自动接管数据的切割、模型的重训
#         self.model.set_validation(
#             method='walk_forward',
#             train_window=50,   # 使用过去 50 个 bar 训练
#             rolling_step=10,   # 每 10 个 bar 重训一次
#             frequency='1m',    # 数据频率
#             incremental=False, # 是否增量训练 (Sklearn 支持 partial_fit)
#             verbose=True       # 打印训练日志
#         )

#         # 确保历史数据长度足够 (训练窗口 + 特征计算所需窗口)
#         # 也可以使用 self.warmup_period = 60
#         self.set_history_depth(60)

#     def prepare_features(self, df: pd.DataFrame, mode: str = "training") -> Tuple[Any, Any]:
#         """
#         [必须实现] 特征工程逻辑
#         该函数会被用于训练阶段（生成 X, y）和预测阶段（生成 X）
#         """
#         X = pd.DataFrame()
#         # 特征 1: 1周期收益率
#         X['ret1'] = df['close'].pct_change()
#         # 特征 2: 2周期收益率
#         X['ret2'] = df['close'].pct_change(2)

#         if mode == 'inference':
#             # 推理模式：只返回最后一行特征，不需要 y
#             # 注意：inference 时传入的 df 是最近 history_depth 的数据
#             # 最后一行是最新的 bar，我们需要它的特征
#             return X.iloc[-1:]

#         # 训练模式：构造标签 y (预测下一期的涨跌)
#         # shift(-1) 把未来的收益挪到当前行作为 label
#         future_ret = df['close'].pct_change().shift(-1)

#         # Combine into one DataFrame to align drops
#         data = pd.concat([X, future_ret.rename("future_ret")], axis=1)

#         # Drop rows with NaN features (e.g. from history padding or initial pct_change)
#         data = data.dropna(subset=["ret1", "ret2"])

#         # For training, we must have a valid future return
#         data = data.dropna(subset=["future_ret"])

#         # Calculate y on valid data
#         y = (data["future_ret"] > 0).astype(int)
#         X_clean = data[["ret1", "ret2"]]

#         return X_clean, y

#     def on_bar(self, bar):
#         # 3. 实时预测与交易

#         # 获取最近的数据进行特征提取
#         # 注意：需要足够的历史长度来计算特征 (例如 pct_change(2) 需要至少3根bar)
#         hist_df = self.get_history_df(10)

#         # 如果数据不足，直接返回
#         if len(hist_df) < 5:
#             return

#         # 复用特征计算逻辑！
#         # 直接调用 prepare_features 获取当前特征
#         X_curr = self.prepare_features(hist_df, mode='inference')

#         try:
#             # 获取预测信号 (概率)
#             # SklearnAdapter 对于二分类返回 Class 1 的概率
#             signal = self.model.predict(X_curr)[0]

#             # 打印信号方便观察
#             # print(f"Time: {bar.timestamp}, Signal: {signal:.4f}")

#             # 结合风控规则下单
#             # 使用 self.get_position(symbol) 获取持仓
#             pos = self.get_position(bar.symbol)

#             if signal > 0.55 and pos == 0:
#                 self.buy(bar.symbol, 300)
#             elif signal < 0.45 and pos > 0:
#                 self.sell(bar.symbol, pos)

#         except Exception:
#             # 模型可能尚未初始化或训练失败
#             pass

# 策略十三：窄幅盘整后放量突破买入，跌破60日均线卖出
# 买入条件：
#     - 连续8天以上每日涨跌幅 ≤ 3%
#     - 随后某一天涨幅 ≥ 5% 且成交量 ≥ 前一日成交量的2倍
# 卖出条件：
#     - 价格收盘跌破60日均线（下穿）
from datetime import date
class NarrowRangeBreakoutStrategy(aq.Strategy):

    def __init__(self,
                 narrow_days=4,
                 narrow_threshold=0.03,
                 breakout_threshold=0.05,
                 volume_ratio=2,
                 ma_period=60):
        self.narrow_days = narrow_days
        self.narrow_threshold = narrow_threshold
        self.breakout_threshold = breakout_threshold
        self.volume_ratio = volume_ratio
        self.ma_period = ma_period
        self.set_history_depth(ma_period + narrow_days + 5)

    def on_bar(self, bar: aq.Bar):
        # 获取历史数据（不含当前bar）
        history = self.get_history_df(self.ma_period + self.narrow_days + 5, bar.symbol)
        if len(history) < self.ma_period + self.narrow_days:
            return

        position = self.get_position(bar.symbol)

        # ---------- 计算均线 ----------
        # 昨日60日均线（基于历史最后60日收盘价）
        prev_ma60 = history['close'].iloc[-self.ma_period:].mean()

        # 今日60日均线（包含今日收盘价）
        recent_closes = history['close'].iloc[-(self.ma_period-1):].tolist()
        recent_closes.append(bar.close)
        ma60 = sum(recent_closes) / self.ma_period

        # 昨日数据
        prev_bar = history.iloc[-2]
        prev_close = prev_bar['close']
        prev_volume = prev_bar['volume']
        # logging.info(f"bar {bar.timestamp_str}")
        # last_sell = False
        # if bar.timestamp_str == "2026-02-27 00:00:00":
        #     logging.info(f"last_sell: True  and position: {position}")
        #     last_sell = True

        from datetime import datetime, timedelta
        # 获取当前日期时间
        today = datetime.now()
        # 计算昨天的日期（同时将时分秒置为 0）
        yesterday_midnight = (today - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        # 格式化输出
        last_date_str = yesterday_midnight.strftime("%Y-%m-%d %H:%M:%S")
        # ---------- 买入信号（空仓） ----------
        if position == 0:
            # 检查过去 narrow_days 天是否连续窄幅（涨跌幅绝对值 ≤ 阈值）
            narrow_ok = True
            for i in range(-self.narrow_days, -1):   # i = -8, -7, ..., -1
                close_today = history.iloc[i]['close']
                close_yesterday = history.iloc[i-1]['close']
                daily_return = (close_today - close_yesterday) / close_yesterday
                logging.info(f"close_yesterday: {close_yesterday}, close_today:{close_today}, daily_return: {abs(daily_return)}")
                if abs(daily_return) >= self.narrow_threshold:
                    # logging.info(f"close_today:{close_today}, close_yesterday: {close_yesterday}, daily_return: {abs(daily_return)}")
                    narrow_ok = False
                    break

            if narrow_ok:
                # 今日涨幅和成交量放大
                price_change = (bar.close - prev_close) / prev_close
                volume_surge = bar.volume >= self.volume_ratio * prev_volume
                logging.info(f"prev_close: {prev_close},bar.close: {bar.close},price_change: {price_change}")
                if price_change >= self.breakout_threshold: #and volume_surge:
                    # 可添加日志：
                    logging.info(f"Buy {bar.symbol} at {bar.close} on {bar.timestamp_str}")
                    self.buy(bar.symbol, 1000)

        # ---------- 卖出信号（持仓） ----------
        # elif position > 0 and last_sell:
        #     logging.info(f"Sell {bar.symbol} at {bar.close} on {bar.timestamp_str}")
        #     self.sell(bar.symbol, 1000)
        elif bar.timestamp_str == last_date_str and position > 0:
            # 下穿60日均线：昨日收盘价 ≥ 昨日均线，今日收盘价 < 今日均线
            if prev_close >= prev_ma60 and bar.close < ma60:
                # 可添加日志：
                logging.info(f"Sell {bar.symbol} at {bar.close} on {bar.timestamp_str}")
                self.sell(bar.symbol, 1000)
        elif position > 0:
            # 下穿60日均线：昨日收盘价 ≥ 昨日均线，今日收盘价 < 今日均线
            if prev_close >= prev_ma60 and bar.close < ma60:
                # 可添加日志：
                logging.info(f"Sell {bar.symbol} at {bar.close} on {bar.timestamp_str}")
                self.sell(bar.symbol, 1000)

# 定义一个简单的策略 (与回测完全一致)
class LiveDemoStrategy(Strategy):
    """实盘演示策略."""

    def on_bar(self, bar: Bar) -> None:
        """收到 Bar 事件的回调."""
        self.log(f"[Live] Received Bar: {bar.symbol} @ {bar.close}")

        # 简单的双均线逻辑
        closes = self.get_history(20, bar.symbol, "close")
        if len(closes) < 20:
            return

        ma5 = closes[-5:].mean()
        ma20 = closes[-20:].mean()

        pos = self.get_position(bar.symbol)

        if ma5 > ma20 and pos == 0:
            self.log("金叉 -> 买入开仓")
            self.buy(bar.symbol, 1)
        elif ma5 < ma20 and pos > 0:
            self.log("死叉 -> 卖出平仓")
            self.close_position(bar.symbol)



import requests
import pandas as pd
from typing import Dict, List, Optional

#该函数会随机从10种策略中选取其中3个策略来测试，并比较最终的结果：
# 1、选取赢率最高的策略；
# 2、交易笔数最少；
# 3、根据该策略启动实时或者模拟盘
#背后的逻辑是，不同的市场和股票，对某种策略会比较敏感，
#并将最终比较的结果传递出来，告诉针对这只股票采用哪种策略比较好。

class StrategyEngine:
    def __init__(self):
        # self._env_path = env_path or self._resolve_env_path()
        # self._lock = threading.RLock()
        pass
    
    
    def run_strategy(
        self,
        code: str
    ) -> Dict[str, Any]:
        """
        随机选择三个策略，并行执行回测，选出总收益率最高且交易次数最少的策略。
        返回结果中包含最优策略的指标及报告路径。
        """
        # 所有可用策略类列表
        strategy_classes = [
            DualSMAStrategy,
            RSIStrategy,
            BollingerStrategy,
            DonchianBreakoutStrategy,
            BollingerRSIStrategy,
            KDJStrategy,
            VWAPStrategy,
            TurtleStrategy,
            FibonacciRetracementStrategy,
            KeltnerChannelStrategy,
            CDMAStrategy,
            TailBuyStrategy,
            # WalkForwardStrategy,
            NarrowRangeBreakoutStrategy
        ]

        # 随机选取三个不重复的策略
        selected_classes = random.sample(strategy_classes, 5)
        # selected_classes = [NarrowRangeBreakoutStrategy]

        # 1. 获取股票数据
        manager = DataFetcherManager()
        today = pd.Timestamp.now().date()
        six_months_ago = today - pd.DateOffset(months=6)
        start_date = six_months_ago.strftime("%Y%m%d")
        end_date = today.strftime("%Y%m%d")
        df = manager.get_daily_data(stock_code=code, start_date=start_date, end_date=end_date)
        df = df[0]  # 假设返回的是列表，取第一个DataFrame

        # 2. 定义单策略运行函数
        def run_single(strategy_class):
            strategy_name = strategy_class.__name__
            try:
                # 运行回测（传入策略类，框架会使用默认参数实例化）
                result = aq.run_backtest(
                    data=df,
                    strategy=strategy_class,
                    symbol=code
                )
                # logging.info(f"result.orders_df:\n {result.orders_df}")
               
                # 提取指标
                metrics = result.metrics_df
                # total_return = metrics.loc['total_pnl', 'value']

                #包含了最后的现金和股票市值
                equity_curve = result.equity_curve
                total_return = equity_curve.iloc[-1] - result.initial_cash

                # 获取交易次数（兼容不同字段名）
                try:
                    num_trades = metrics.loc['trade_count', 'value']
                except KeyError:
                    num_trades = len(result.trades) if hasattr(result, 'trades') else 0

                return {
                    'name': strategy_name,
                    'result': result,
                    'total_return': total_return,
                    'num_trades': num_trades,
                    'orders_df': result.orders_df,
                    'trades_df':result.trades_df
                }
            except Exception as e:
                logging.error(f"策略 {strategy_name} 运行失败: {e}")
                return None

        # 3. 多线程并行执行三个策略
        results = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_map = {executor.submit(run_single, cls): cls for cls in selected_classes}
            for future in as_completed(future_map):
                res = future.result()
                if res is not None:
                    # logging.info(f"res:\n{res}")
                    # logging.info(f"res.orders_df:\n{res.get('orders_df')}")
                    results.append(res)

        # logging.info(f"result len: {len(results)}")
        if not results:
            raise RuntimeError("所有策略均运行失败，无法选出最优策略。")

        # 4. 选择最优策略：总收益率最高，若相同则选交易次数最少的
        # best = max(results, key=lambda x: (x['total_return'], -x['num_trades']))
        # logging.info(f"results:\n{results[0]}")

        best = max(results, key=lambda x: (x['total_return']))

        # logging.info(f"best:\n{best}")
        best_result = best['result']
        # logging.info(f"best_result:\n{best_result}")
        best_name = best['name']

        # 5. 为最优策略生成报告（文件名包含策略名，避免覆盖）
        report_filename = f"./static/images/{code}_{best_name}_report.html"
        dashboard_filename = f"./static/images/{code}_{best_name}_dashboard.html"

        best_result.report(
            title=f"策略报告 - {best_name}",
            filename=report_filename,
            show=False
        )

        aqp.plot_dashboard(
            result=best_result,
            title=f"策略仪表盘 - {best_name}",
            show=False,
            filename=dashboard_filename
        )

        # ========== 6. 绘制 K 线图并叠加买卖点 ==========
        # 提取买卖点（从 orders_df 或 trades 中获取）

        plt.rcParams["font.family"] = "Microsoft YaHei"
        plt.rcParams["axes.unicode_minus"] = False
        
        # ---------- 关键修正：处理日期索引 ----------
        # 将 date 列转换为 DatetimeIndex 并设为索引
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)

        # 重命名列为 mplfinance 所需的标准大写（虽然 mplfinance 新版支持小写，但明确大写更保险）
        df.rename(columns={
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'volume': 'Volume'
        }, inplace=True)

        # 按日期升序排列
        # ----- 确保索引为 DatetimeIndex 并按日期升序 -----
        df.index = pd.DatetimeIndex(df.index)   # 关键修改：强制转换为 DatetimeIndex
        df.sort_index(inplace=True)

        # logging.info(f"df.head\n{df.head}")
        # logging.info(f"best.get('orders_df')\n{best.get('orders_df').head}")
        # logging.info(f"best.get('trades_df')\n{best.get('trades_df').head}")
        # logging.info(f"列名: \n{best.get('orders_df').columns.tolist()}")
        # logging.info(f"列名: \n{best.get('trades_df').columns.tolist()}")

        buy_signals = []
        sell_signals = []

# orders 列名
# ['id', 'symbol', 'side', 'order_type', 'quantity', 'filled_quantity', 
# 'limit_price', 'stop_price', 'avg_price', 'commission', 'status', 'time_in_force', 
# 'created_at', 'updated_at', 'tag', 'reject_reason', 'filled_value', 'duration']

# 2026-02-24 21:35:15 | INFO     | root                 | trades 列名:
# ['symbol', 'entry_time', 'exit_time', 'entry_price', 'exit_price', 'quantity', 
# 'side', 'pnl', 'net_pnl', 'return_pct', 'commission', 'duration_bars', 'duration', 
# 'mae', 'mfe', 'entry_tag', 'exit_tag', 'entry_portfolio_value', 'max_drawdown_pct']

        # 尝试从 orders_df 提取（假设每行包含一笔完整交易）
        if best.get('trades_df') is not None:
            trades = best.get('trades_df')
            # 根据实际列名调整，以下为常见命名
            for index,row in trades.iterrows():
                # 只考虑多头交易
                # logging.info(f"row=:{row}")
                entry_time = pd.to_datetime(row['entry_time'])
                exit_time = pd.to_datetime(row['exit_time'])
                buy_signals.append((entry_time, row['entry_price']))
                sell_signals.append((exit_time, row['exit_price']))
        else:
            logging.warning("无法从回测结果中提取买卖点，将只绘制 K 线图。")
        
        # 由于trades_df中只保留了开仓和平仓发生，而没有考虑仅仅买入，但没有卖出，一直持有的情况
        # 所以需要对最后一次开仓添加买入信号：

        if (int(best['total_return'])) != 0 and int(best['num_trades']) == 0:
            create_date = pd.to_datetime(best.get('orders_df').iloc[-1]['created_at'])
            avg_price = best.get('orders_df').iloc[-1]['avg_price']
            logging.info(f"avg_price: {avg_price} on pd.to_datetime: {create_date}")
            buy_signals.append((create_date, avg_price))

        logging.info(f"buy_signals: {len(buy_signals)} and sell_signals: {len(sell_signals)}")
        # 设置图片保存路径
        image_dir = "./static/images"
        chart_filename = f"{code}_{best_name}_chart.png"
        chart_path = os.path.join(image_dir, chart_filename)
        ###############################################################
        def align_signal_dates(signals, df):
            """
            将信号日期与 df 的索引对齐：
            1. 去除时区信息
            2. 若日期不存在，则取该日期之前的最近一个交易日（asof）
            3. 返回可用的 (位置索引, 价格) 列表
            """
            aligned = []
            for dt, price in signals:
                # 去除时区，得到无时区的 Timestamp
                if dt.tz is not None:
                    dt = dt.tz_localize(None)   # 或 dt.replace(tzinfo=None)

                # 尝试精确匹配
                if dt in df.index:
                    pos = df.index.get_loc(dt)
                    aligned.append((pos, price))
                else:
                    # 精确匹配失败，取最近的前一个交易日
                    asof_date = df.index.asof(dt)   # 返回 <= dt 的最后一个日期
                    if pd.notna(asof_date):
                        pos = df.index.get_loc(asof_date)
                        logging.info(f"信号日期 {dt} 不在数据中，已对齐到前一个交易日 {asof_date}")
                        aligned.append((pos, price))
                    else:
                        logging.info(f"信号日期 {dt} 之前无有效交易日，已忽略")
            return aligned

        # 在绘图前，对齐信号
        # buy_aligned = buy_signals
        buy_aligned = align_signal_dates(buy_signals, df)
        sell_aligned = align_signal_dates(sell_signals, df)

        logging.info(f"buy_signals: {buy_signals}")
        logging.info(f"sell_signals: {sell_signals}")

        logging.info(f"buy_aligned: {buy_aligned}")
        logging.info(f"sell_aligned: {sell_aligned}")

        # 直接修改 mplfinance 的默认样式
        my_style = mpf.make_mpf_style(
            base_mpf_style='charles',  # 继承你原来用的 'charles' 风格
            rc={
                'font.family': 'Microsoft YaHei',  # 关键：设置中文字体
                'axes.unicode_minus': False        # 解决负号显示问题
            }
        )

        # 绘图（使用 mplfinance）
        fig, axes = mpf.plot(
            df,
            type='candle',
            volume=True,
            # style='charles',
            style=my_style,                     # <--- 使用自定义样式
            returnfig=True,
            figsize=(14, 8),
            xrotation=30,
            datetime_format='%Y-%m-%d',
            tight_layout=True,
            title=f'{code} - {best_name}买卖点',
            ylabel='价格',
            ylabel_lower='成交量'
        )
        ax_main = axes[0]

        # 绘制买入信号
        if buy_aligned:
            buy_positions, buy_prices = zip(*buy_aligned)   # 解压成两个列表
            logging.info(f"buy info: {buy_positions}")
            ax_main.scatter(buy_positions, buy_prices,
                            marker='^', color='blue', s=200, zorder=10,
                            edgecolors='white', linewidths=1.5, label='买入')

        # 绘制卖出信号
        if sell_aligned:
            sell_positions, sell_prices = zip(*sell_aligned)
            logging.info(f"sell info: {sell_positions}")
            ax_main.scatter(sell_positions, sell_prices,
                            marker='v', color='red', s=200, zorder=10,
                            edgecolors='white', linewidths=1.5, label='卖出')


        # 添加图例（去重）
        handles, labels = ax_main.get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        if by_label:
            ax_main.legend(by_label.values(), by_label.keys(), fontsize=12)

        plt.savefig(chart_path, dpi=150, bbox_inches='tight')
        plt.close(fig)

        # # self.CTPLiveTrade()
        # rank_data = self.fetch_eastmoney_rank()
        # if rank_data:
        #     self.display_stocks(rank_data)

        # 7. 构建返回结果
        return {
            "code": code,
            "summary": f"/images/{code}_{best_name}_dashboard.html\n,"
                       f"/images/{code}_{best_name}_report.html",
            "metrics": {
                "totalReturn": best['total_return'],
                "maxDrawdown": best_result.metrics_df.loc['max_drawdown', 'value']/10000,
                "sharpeRatio": best_result.metrics_df.loc['sharpe_ratio', 'value'],
                "winRate": best_result.metrics_df.loc['win_rate', 'value']   #,
                # "numTrades": best['num_trades']
            },
            # "best_strategy": best_name,
            "chartUrl": f"./images/{chart_filename}"  # 保留原字段
        }
    

    def CTPLiveTrade(self):
        logging.info("正在配置实盘环境...")

        # 1. 定义交易标的
        # 实盘中，合约乘数等信息通常可以从柜台自动查询，但显式配置更安全
        rb2310 = Instrument(
            symbol="002155",
            asset_type=aq.AssetType.Futures,
            multiplier=10,
            margin_ratio=0.1,
        )

        # 2. CTP 账户配置 (请替换为你的真实账户或 SimNow 模拟账户)
        CTP_CONFIG = {
            "md_front": "tcp://180.168.146.187:10131",  # SimNow 行情前置
            "td_front": "tcp://180.168.146.187:10130",  # SimNow 交易前置
            "broker_id": "9999",
            "user_id": "guochunrong",
            "password": "GuoChunRong!23",
            "app_id": "simnow_client_test",
            "auth_code": "0000000000000000",
        }

        # 3. 创建实盘运行器
        try:
            runner = LiveRunner(
                strategy_cls=LiveDemoStrategy,
                instruments=[rb2310],
                md_front=CTP_CONFIG["md_front"],
                td_front=CTP_CONFIG["td_front"],
                broker_id=CTP_CONFIG["broker_id"],
                user_id=CTP_CONFIG["user_id"],
                password=CTP_CONFIG["password"],
                app_id=CTP_CONFIG["app_id"],
                auth_code=CTP_CONFIG["auth_code"],
            )

            # 4. 启动实盘
            # run() 会阻塞主线程，直到手动停止 (Ctrl+C)
            logging.info("启动 CTP 接口...")
            runner.run(cash=500_000)

        except ImportError:
            logging.info(
                "错误: 未找到 CTP 接口库。请确保已安装 akquant[ctp] 或手动配置 "
                "thosttraderapi。"
            )
        except Exception as e:
            logging.info(f"实盘启动失败: {e}")
    """
    第 11 章：实盘交易系统 (Live Trading).

    本示例展示了如何将策略部署到实盘环境。
    AKQuant 支持通过 CTP 接口连接期货公司柜台，实现行情接收和自动交易。

    注意：
    1. 实盘交易涉及真实资金，请务必在模拟盘 (SimNow) 充分测试。
    2. 本代码仅为配置演示，无法直接运行，因为需要有效的 CTP 账户信息。
    3. 你需要安装 CTP 驱动 (通常只支持 Linux/Windows)。

    配置流程：
    1. 准备 CTP 账户 (BrokerID, UserID, Password, AuthCode, AppID)。
    2. 获取前置机地址 (MD Front, TD Front)。
    3. 配置 LiveRunner 并启动。
    """


    def fetch_eastmoney_rank(self,limit=100) -> Optional[List[Dict]]:
        """
        获取东方财富个股人气榜或飙升榜数据

        Args:
            page: 页码，从1开始
            rank_type: 榜单类型，"人气榜" 或 "飙升榜"

        Returns:
            包含股票数据的列表，每个元素是一个字典，失败返回None
        """
        """
        获取东方财富股吧人气榜数据
        :param limit: 获取的股票数量
        """
        # 接口地址 (这是东财人气榜通用的数据中心接口)
        base_url = "https://emweb.securities.eastmoney.com/PC_MarketTerminal/Notice/GetNoticeStockRanking"
        
        # 构造请求参数
        params = {
            "pageIndex": 1,
            "pageSize": limit,
            "sort": "Ranking",
            "asc": "true",
            "marketType": 0,
            "_": int(time.time() * 1000)  # 时间戳
        }
        
        # 设置请求头，必须包含 Referer，否则会被拦截
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Referer": "https://guba.eastmoney.com/rank/",
            "Accept": "application/json, text/javascript, */*; q=0.01"
        }
        # params=params,
        try:
            response = requests.get(base_url,params=params,headers=headers, timeout=10)
            response.raise_for_status()  # 检查请求是否成功

            data = response.json()
            logging.info(f"data:{data}")
            # 检查返回的数据是否包含我们需要的列表
            if data and data.get('code') == 0 and data.get('result'):
                # 'data' 字段下才是真正的股票数据列表
                stock_list = data['result']['data']
                logging.info(f"成功获取 页，共 {len(stock_list)} 条数据。")
                return stock_list
            else:
                logging.info(f"获取数据失败，返回信息: {data}")
                return None

        except requests.exceptions.RequestException as e:
            logging.info(f"网络请求错误: {e}")
            return None
        except ValueError as e:
            logging.info(f"JSON解析错误: {e}")
            return None

    def display_stocks(self,stock_list: List[Dict]):
        """将股票数据列表显示为表格"""
        if not stock_list:
            logging.info("没有数据可显示。")
            return

        # 提取需要显示的字段，并设置中文列名
        display_data = []
        for item in stock_list:
            display_data.append({
                "排名": item.get('RANK', ''),
                "代码": item.get('SECURITY_CODE', ''),
                "名称": item.get('SECURITY_NAME_ABBR', ''),
                "最新价": item.get('LATEST_PRICE', ''),
                "涨跌幅": f"{item.get('CHANGE_RATE', 0)*100:.2f}%" if item.get('CHANGE_RATE') else '',
                "涨跌额": item.get('CHANGE', ''),
                "最新粉丝": item.get('NEW_FANS', ''),
                "铁杆粉丝": item.get('IRON_FANS', ''),
            })

        # 使用pandas打印美观的表格
        df = pd.DataFrame(display_data)
        logging.info(df.to_string(index=False))

# if __name__ == "__main__":
#     logging.info("=== 东方财富个股人气榜 (第1页) ===")
#     rank_data = fetch_eastmoney_rank(page=1, rank_type="人气榜")
#     if rank_data:
#         display_stocks(rank_data)

#     logging.info("\n=== 东方财富个股飙升榜 (第1页) ===")
#     soar_data = fetch_eastmoney_rank(page=1, rank_type="飙升榜")
#     if soar_data:
#         display_stocks(soar_data)

    # 可选：将数据保存到CSV文件
    # if rank_data:
    #     df_rank = pd.DataFrame(rank_data)
    #     df_rank.to_csv('人气榜.csv', index=False, encoding='utf_8_sig')
    # if soar_data:
    #     df_soar = pd.DataFrame(soar_data)
    #     df_soar.to_csv('飙升榜.csv', index=False, encoding='utf_8_sig')