from src.scheduler import run_with_schedule
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import concurrent.futures
import sys
import json
import os
from data_provider.base import DataFetcherManager
import time

def get_stock_kline(symbol, date):
        """
        获取指定股票在指定日期和前一天的日线数据
        返回 (open, high, close, prev_close) 如果数据完整，否则返回None
        """
        try:
            # 日期格式转换
            if isinstance(date, str):
                date = datetime.strptime(date, '%Y-%m-%d').date()
            # 获取当天和前一天的日期范围
            start_date = (date - timedelta(days=1)).strftime('%Y%m%d')
            end_date = date.strftime('%Y%m%d')
            print(f"start_date:{start_date} end_date: {end_date}")

            manager = DataFetcherManager()
            df, source = manager.get_daily_data(stock_code=symbol, days=2)

            # df = ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date=start_date, end_date=end_date, adjust="")
            if df.empty or len(df) < 2:
                # 如果少于2天数据，无法获得前一天收盘价
                return None
            # 假设日期列名为'日期'，需要检查实际列名，通常返回的列有'日期','开盘','收盘','最高','最低'等
            # 确保日期是datetime格式并排序
            # ['date', 'open', 'high', 'low', 'close', 'volume', 'amount', 'pct_chg']
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            # 获取当天数据（最后一天）
            today_data = df.iloc[-1]
            # 获取前一天数据（倒数第二天）
            prev_data = df.iloc[-2]
            # 提取字段
            open_price = today_data['open']
            high_price = today_data['high']
            close_price = today_data['close']
            prev_close = prev_data['close']
            time.sleep(1)
            return open_price, high_price, close_price, prev_close
        except Exception as e:
            print(f"Error fetching {symbol} on {date}: {e}")
            return None

# 2. 并发获取每只股票最近9天数据
def fetch_stock_data(code, name):
    try:
        start_date = (datetime.now() - timedelta(days=60)).strftime('%Y%m%d')
        hist = ak.stock_zh_a_hist(symbol=code, period="daily", start_date=start_date, adjust="")
        if len(hist) >= 9:
            hist = hist.tail(9).copy()
            hist['股票代码'] = code
            hist['股票名称'] = name
            return hist
        else:
            return None
    except Exception:
        return None

def breakout_stock():
    # 1. 获取所有股票代码和名称
    # 获取所有A股基本信息（包含代码和名称）
    spot_df = ak.stock_comment_em()
    df_sorted = spot_df.sort_values(
        by=['上升'],
        ascending=False
    ).reset_index(drop=True)
    # 提取代码和名称列（实际列名可能略有不同，请根据实际情况调整）
    spot_df = df_sorted.loc[~df_sorted['代码'].str.startswith('8')] 
    spot_df = spot_df.loc[~spot_df['代码'].str.startswith('b')] 
    stocks = spot_df[['代码','名称']].copy()
    print(stocks.head(5))

    # 存储符合条件的股票信息
    valid_records = []

    # 遍历每只股票，检查条件
    count = 0
    for _, row in stocks.iterrows():
        count +=1
        if count > 2000:
            break
        code = row['代码']
        name = row['名称']
        print(code)
        try:
            # 获取足够的历史日线数据（至少9个交易日）
            start_date = (datetime.now() - timedelta(days=20)).strftime('%Y%m%d')
            print(start_date)
            hist = ak.stock_zh_a_hist(
                symbol=code,
                period="daily",
                start_date=start_date,
                adjust=""
            )

            print(hist)
            print("涨跌幅：")

            if len(hist) < 9:
                continue  # 数据不足

            # 按日期排序，取最近9天（含当天）
            hist = hist.sort_values('日期').tail(10).copy()
            # 计算每日涨跌幅（百分比）
            hist['涨跌幅'] = hist['收盘'].pct_change() * 100

            # 条件1：前8天每日涨跌幅绝对值 ≤ 3%
            # 前8天对应索引1~8（pct_change后第0行为NaN）
            prev_8_changes = []
            for i in range(-6,-1):
                prev_8_changes.append(hist['涨跌幅'].iloc[i])

            print(prev_8_changes)
            prev_8_changes = pd.DataFrame(prev_8_changes)
            print("涨跌幅：")
            print(prev_8_changes)

            if (prev_8_changes.abs() > 3).any():
                continue

            # 条件2：当天涨幅 > 6%
            today_change = hist['涨跌幅'].iloc[-1]
            if today_change <= 6:
                continue

            # 条件3：当天成交量 ≥ 1.5 × 前9天平均成交量
            avg_volume = hist['成交量'].mean()
            if hist['成交量'].iloc[-1] < 1.5 * avg_volume:
                continue

            # 满足所有条件，记录股票信息
            valid_records.append({
                '代码': code,
                '名称': name,
                '交易日': hist['日期'].iloc[-1]  # 保留为Timestamp，稍后格式化
            })
        except Exception:
            # 忽略异常股票，继续下一只
            continue

    
    if len(valid_records) == 0:
        return 
    # 将结果转换为DataFrame
    df_valid = pd.DataFrame(valid_records)
    print("df_valid:")
    print(df_valid)

    # 列映射（与原样式保持一致）
    columns_map = {
        '代码': 'stockCode',
        '名称': 'stockName',
        '交易日': 'date'
    }

    # 仿照原样式链式处理：取前50 → 选择列 → 重命名 → 格式化日期 → 转字典列表
    result = (df_valid
            .head(50)[list(columns_map.keys())]
            .rename(columns=columns_map)
            .assign(date=lambda x: pd.to_datetime(x['date']).dt.strftime('%Y-%m-%d'))
            .to_dict('records')
            )

    data = result.copy()

    # 将 data 存储到本地文件
    file_path = './data/breakout_stock_data.json'  # 可根据需要修改路径
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # # 从本地文件读取数据，重新赋值给 data
    # with open(file_path, 'r', encoding='utf-8') as f:
    #     data = json.load(f)
    # print(data)
def sentiment_rising():
    comments_df = ak.stock_comment_em()
    df_sorted = comments_df.sort_values(
        by=['上升'],
        ascending=False
    ).reset_index(drop=True)

    # 先过滤掉代码以8开头的股票，避免不必要的API调用
    df_filtered = df_sorted[~df_sorted['代码'].str.startswith('8')].copy()

    # 应用新的条件
    count = 0
    valid_rows = []
    for idx, row in df_filtered.iterrows():
        count +=1
        if count > 200:
            break
        code = row['代码']
        date = row['交易日']  # 假设列名为'交易日'
        # 检查上升列是否为真（根据实际含义，可能需要判断）
        # 如果上升列是数值，且大于0表示上升
        if row.get('上升', 0) <= 0:  # 假设上升列是数值，0表示不上升
            continue
        # 获取K线数据
        print(f"code:{code}")
        kline = get_stock_kline(code, date)
        if kline is None:
            continue
        open_price, high_price, close_price, prev_close = kline

        print(f"code: {code} open_price:{open_price} high_price: {high_price}")
        # 收阳条件：收盘 > 昨收 且 收盘 > 开盘
        if not (close_price > prev_close and close_price > open_price):
            continue
        # 不能长上影线：最高价回撤不超过5% (最高-收盘)/最高 <= 5%
        if (high_price - close_price) / high_price > 0.05:
            continue
            # 通过所有条件，保留该行
        valid_rows.append(row)

    # 构建新的DataFrame，包含符合条件的行
    df_valid = pd.DataFrame(valid_rows)

    # 如果valid_rows为空，则结果为空列表
    result = []

    if df_valid.empty != True:
        # 取前50
        df_top50 = df_valid.head(50)
        columns_map = {
            '代码': 'stockCode',
            '名称': 'stockName',
            '交易日': 'date'
        }
        result = (df_top50[list(columns_map.keys())]
                .rename(columns=columns_map)
                .assign(date=lambda x: pd.to_datetime(x['date']).dt.strftime('%Y-%m-%d'))
                .to_dict('records')
                )
    data = result.copy()
    # 将 data 存储到本地文件
    file_path = './data/sentiment_rising_stock_data.json'  # 可根据需要修改路径
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def main()->int:
    # run_with_schedule(
    #     task=breakout_stock,
    #     schedule_time='08:30',
    #     run_immediately=True
    # )
    breakout_stock()
    sentiment_rising()
    return 0

if __name__ == "__main__":
    sys.exit(main())