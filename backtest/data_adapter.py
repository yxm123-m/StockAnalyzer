"""
Backtrader PandasData 适配器 — 将 akshare 数据转为 backtrader 可识别的格式
"""
import pandas as pd
import backtrader as bt


class ASharePandasData(bt.feeds.PandasData):
    """
    自定义 PandasData，在标准 OHLCV 基础上增加集合竞价数据行
    额外行: auction_score, auction_vol_ratio, open_gap_pct
    """
    lines = ('auction_score', 'auction_vol_ratio', 'open_gap_pct',)

    # 列索引映射 (DataFrame column index)
    params = (
        ('datetime', 0),
        ('open', 1),
        ('high', 2),
        ('low', 3),
        ('close', 4),
        ('volume', 5),
        ('openinterest', -1),
        ('auction_score', 6),
        ('auction_vol_ratio', 7),
        ('open_gap_pct', 8),
    )


def prepare_backtest_data(code, start_date, end_date):
    """
    准备单只股票的回测数据
    返回: DataFrame with columns [datetime, open, high, low, close, volume,
                                   auction_score, auction_vol_ratio, open_gap_pct]
    或 None (数据不足时)
    """
    from data.fetcher import fetch_daily_kline
    from data.database import get_call_auction

    # 获取日K线
    sd = start_date.replace('-', '')
    ed = end_date.replace('-', '')
    kline = fetch_daily_kline(code, sd, ed)

    if kline is None or kline.empty or len(kline) < 50:
        return None

    # 获取竞价数据
    auctions = get_call_auction(code=code)
    auction_map = {}
    for a in auctions:
        auction_map[a['trade_date']] = a

    # 合并数据
    rows = []
    for _, row in kline.iterrows():
        date = row['trade_date']
        auction = auction_map.get(date, {})

        rows.append({
            'datetime': pd.to_datetime(date),
            'open': row['open'],
            'high': row['high'],
            'low': row['low'],
            'close': row['close'],
            'volume': row['volume'],
            'auction_score': auction.get('total_score', 0),
            'auction_vol_ratio': auction.get('vol_ratio_vs_ma20', 1.0),
            'open_gap_pct': auction.get('open_gap_pct', 0),
        })

    df = pd.DataFrame(rows)
    df = df.sort_values('datetime').reset_index(drop=True)
    # backtrader 需要 datetime 作为索引
    df = df.set_index('datetime')
    return df
