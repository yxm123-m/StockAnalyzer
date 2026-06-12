"""
Backtrader PandasData 适配器 — 将 akshare 数据转为 backtrader 可识别的格式

尾盘狙击版: 包含 eod_score, close_position, eod_vol_ratio 等尾盘指标
"""
import pandas as pd
import backtrader as bt


class ASharePandasData(bt.feeds.PandasData):
    """
    自定义 PandasData，在标准 OHLCV 基础上增加尾盘数据行
    额外行: eod_score, close_position, eod_vol_ratio, daily_change_pct
    """
    lines = ('eod_score', 'close_position', 'eod_vol_ratio', 'daily_change_pct',)

    # 列索引映射 (DataFrame column index)
    params = (
        ('datetime', 0),
        ('open', 1),
        ('high', 2),
        ('low', 3),
        ('close', 4),
        ('volume', 5),
        ('openinterest', -1),
        ('eod_score', 6),
        ('close_position', 7),
        ('eod_vol_ratio', 8),
        ('daily_change_pct', 9),
    )


def prepare_backtest_data(code, start_date, end_date):
    """
    准备单只股票的回测数据
    返回: DataFrame with columns [datetime, open, high, low, close, volume,
                                   eod_score, close_position, eod_vol_ratio, daily_change_pct]
    或 None (数据不足时)
    """
    from data.fetcher import fetch_daily_kline
    from data.database import get_eod_data

    # 获取日K线
    sd = start_date.replace('-', '')
    ed = end_date.replace('-', '')
    kline = fetch_daily_kline(code, sd, ed)

    if kline is None or kline.empty or len(kline) < 50:
        return None

    # 获取尾盘数据
    eod_list = get_eod_data(code=code)
    eod_map = {}
    for e in eod_list:
        eod_map[e['trade_date']] = e

    # 合并数据
    rows = []
    for _, row in kline.iterrows():
        date = row['trade_date']
        eod = eod_map.get(date, {})

        rows.append({
            'datetime': pd.to_datetime(date),
            'open': row['open'],
            'high': row['high'],
            'low': row['low'],
            'close': row['close'],
            'volume': row['volume'],
            'eod_score': eod.get('total_score', 0),
            'close_position': eod.get('close_position', 0.5),
            'eod_vol_ratio': eod.get('eod_vol_ratio', 1.0),
            'daily_change_pct': eod.get('daily_change_pct', 0),
        })

    df = pd.DataFrame(rows)
    df = df.sort_values('datetime').reset_index(drop=True)
    df = df.set_index('datetime')
    return df
