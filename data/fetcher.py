"""
通用数据获取 — 封装 akshare 接口
"""
import pandas as pd
from datetime import datetime, timedelta

from data.database import (
    save_stock_list, get_all_stocks,
    save_daily_kline, get_daily_kline
)


def fetch_stock_list(force_refresh=False):
    """获取A股股票列表，优先从缓存读取"""
    cached = get_all_stocks()
    if cached and not force_refresh:
        return pd.DataFrame(cached)

    try:
        import akshare as ak
        # 获取沪深A股列表
        df = ak.stock_zh_a_spot_em()
        if df is None or df.empty:
            print("[WARN] stock_zh_a_spot_em() returned empty")
            return pd.DataFrame()

        # 提取所需字段
        records = []
        for _, row in df.iterrows():
            code = str(row.get('代码', '')).strip()
            name = str(row.get('名称', '')).strip()
            if not code:
                continue
            # 判断市场: 6开头=上海, 0/3开头=深圳
            market = 'SH' if code.startswith(('6', '9')) else 'SZ'
            records.append((code, name, market))
            if len(records) >= 5000:
                break

        save_stock_list(records)
        return pd.DataFrame(records, columns=['code', 'name', 'market'])

    except Exception as e:
        print(f"[ERROR] fetch_stock_list: {e}")
        return pd.DataFrame(cached) if cached else pd.DataFrame()


def fetch_index_daily(symbol="sh000001", start_date="20240101", end_date=None):
    """获取指数日K线"""
    if end_date is None:
        end_date = datetime.now().strftime("%Y%m%d")

    try:
        import akshare as ak
        df = ak.stock_zh_index_daily(symbol=symbol)
        if df is None or df.empty:
            return pd.DataFrame()

        df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
        mask = (df['date'] >= start_date[:4] + '-' + start_date[4:6] + '-' + start_date[6:]) & \
               (df['date'] <= end_date[:4] + '-' + end_date[4:6] + '-' + end_date[6:])
        return df[mask]
    except Exception as e:
        print(f"[ERROR] fetch_index_daily({symbol}): {e}")
        return pd.DataFrame()


def fetch_daily_kline(code, start_date="20240101", end_date=None, force_refresh=False):
    """
    获取个股日K线数据，优先从缓存读取
    start_date/end_date: 'YYYYMMDD' 或 'YYYY-MM-DD'
    """
    if end_date is None:
        end_date = datetime.now().strftime("%Y%m%d")

    # 统一日期格式
    sd = start_date.replace('-', '')
    ed = end_date.replace('-', '')

    cached = get_daily_kline(code, sd[:4]+'-'+sd[4:6]+'-'+sd[6:], ed[:4]+'-'+ed[4:6]+'-'+ed[6:])
    if cached and not force_refresh:
        return pd.DataFrame(cached)

    try:
        import akshare as ak
        period = "daily"
        df = ak.stock_zh_a_hist(symbol=code, period=period,
                                start_date=sd, end_date=ed, adjust="qfq")
        if df is None or df.empty:
            return pd.DataFrame()

        df = df.rename(columns={
            '日期': 'trade_date', '开盘': 'open', '最高': 'high',
            '最低': 'low', '收盘': 'close', '成交量': 'volume',
            '成交额': 'amount', '涨跌幅': 'change_pct'
        })
        df['trade_date'] = pd.to_datetime(df['trade_date']).dt.strftime('%Y-%m-%d')

        # 计算前收盘价
        df['pre_close'] = (df['close'] / (1 + df['change_pct'] / 100)).round(2)

        # 缓存到数据库
        records = []
        for _, row in df.iterrows():
            records.append((
                code, row['trade_date'], row['open'], row['high'], row['low'],
                row['close'], row['volume'], row.get('amount', 0),
                row['pre_close'], row['change_pct']
            ))
        if records:
            save_daily_kline(records)

        return df

    except Exception as e:
        print(f"[ERROR] fetch_daily_kline({code}): {e}")
        return pd.DataFrame(cached) if cached else pd.DataFrame()


def fetch_spot_data():
    """获取实时行情快照"""
    try:
        import akshare as ak
        df = ak.stock_zh_a_spot_em()
        if df is not None and not df.empty:
            df = df.rename(columns={
                '代码': 'code', '名称': 'name', '最新价': 'price',
                '涨跌幅': 'change_pct', '涨跌额': 'change',
                '成交量': 'volume', '成交额': 'amount',
                '今开': 'open', '最高': 'high', '最低': 'low',
                '昨收': 'pre_close',
            })
        return df
    except Exception as e:
        print(f"[ERROR] fetch_spot_data: {e}")
        return pd.DataFrame()


def fetch_sectors():
    """获取板块涨跌"""
    try:
        import akshare as ak
        df = ak.stock_sector_fund_flow_rank(indicator="今日", sector_type="行业资金流向")
        return df
    except Exception:
        pass

    # 降级: 获取行业板块
    try:
        import akshare as ak
        df = ak.stock_board_industry_name_em()
        return df
    except Exception as e:
        print(f"[ERROR] fetch_sectors: {e}")
        return pd.DataFrame()
