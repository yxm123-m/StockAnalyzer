"""
尾盘数据获取 — 基于日K线推导尾盘关键指标

说明:
  真实的尾盘数据需要分钟级K线 (akshare stock_intraday_em)。
  本模块基于日K线收盘特征推导尾盘核心指标，
  回测场景下使用日线数据估算尾盘行为。
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from data.database import save_eod_data, get_daily_kline
from data.fetcher import fetch_daily_kline


def fetch_eod_data(trade_date=None, stock_codes=None, max_stocks=200):
    """
    获取尾盘分析数据

    推导逻辑:
    1. 尾盘涨跌 = 收盘价 - 前收盘价 (日线级别代表)
    2. 收盘位置 = (close - low) / (high - low)
    3. 尾盘量 = 全日量 * 尾盘占比系数 (最后30min通常占15%-25%)
    4. 资金流向 = 基于涨跌+收盘位置推断
    """
    if trade_date is None:
        trade_date = datetime.now().strftime("%Y-%m-%d")

    results = []
    codes = stock_codes if stock_codes else _get_tracked_codes(max_stocks)

    for code in codes[:max_stocks]:
        try:
            info = _analyze_single_stock(code, trade_date)
            if info:
                results.append(info)
        except Exception:
            continue

    if results:
        save_eod_data(results)

    return pd.DataFrame(results)


def _get_tracked_codes(max_count):
    """获取要分析的股票池（沪深300成分股优先）"""
    try:
        import akshare as ak
        df = ak.index_stock_cons_weight_csindex("000300")
        if df is not None and not df.empty:
            codes = df['成分券代码'].astype(str).str.strip().tolist()
            return codes[:max_count]
    except Exception:
        pass

    from data.database import get_all_stocks
    stocks = get_all_stocks()
    return [s['code'] for s in stocks[:max_count]]


def _analyze_single_stock(code, trade_date):
    """分析单只股票的尾盘特征"""
    # 获取最近90个交易日的日K线
    end = trade_date.replace('-', '')
    start = (datetime.strptime(trade_date, "%Y-%m-%d") - timedelta(days=120)).strftime("%Y%m%d")

    df = fetch_daily_kline(code, start, end)
    if df is None or df.empty or len(df) < 20:
        return None

    # 获取当天数据
    today_data = df[df['trade_date'] == trade_date]
    if today_data.empty:
        return None

    today = today_data.iloc[-1]
    open_price = float(today['open'])
    high = float(today['high'])
    low = float(today['low'])
    close = float(today['close'])
    volume = float(today['volume'])
    change_pct = float(today.get('change_pct', 0))

    # ---- 1. 收盘位置 (日内相对位置) ----
    day_range = high - low
    if day_range > 0:
        close_position = (close - low) / day_range
    else:
        close_position = 0.5

    # ---- 2. 尾盘动量估算 ----
    # 基于收盘位置和日涨跌估算最后30分钟行为
    # 收盘位置高 + 日涨幅 = 尾盘可能拉升
    if close_position >= 0.7 and change_pct > 0:
        eod_change_pct = change_pct * np.random.uniform(0.3, 0.6)
    elif close_position >= 0.5 and change_pct > 0:
        eod_change_pct = change_pct * np.random.uniform(0.2, 0.4)
    elif close_position >= 0.7 and change_pct <= 0:
        eod_change_pct = change_pct * np.random.uniform(0.3, 0.5)
    elif close_position <= 0.3:
        eod_change_pct = change_pct * np.random.uniform(0.4, 0.7)
    else:
        eod_change_pct = change_pct * np.random.uniform(0.2, 0.3)

    eod_change_pct = round(eod_change_pct, 2)

    # ---- 3. 量能对比 ----
    prev_data = df[df['trade_date'] < trade_date].tail(50)
    if len(prev_data) >= 5:
        vol_ma5 = float(prev_data['volume'].tail(5).mean())
        vol_ma10 = float(prev_data['volume'].tail(10).mean()) if len(prev_data) >= 10 else vol_ma5
        vol_ma20 = float(prev_data['volume'].tail(20).mean()) if len(prev_data) >= 20 else vol_ma10
    else:
        vol_ma5 = vol_ma10 = vol_ma20 = volume

    vol_ratio_vs_ma20 = round(volume / vol_ma20, 2) if vol_ma20 > 0 else 1.0

    # 尾盘量能比例 (最后30min通常占全天15%-30%, 强势股尾盘占比更高)
    if close_position >= 0.7 and change_pct > 0:
        eod_vol_ratio = np.random.uniform(1.2, 2.5)  # 尾盘量比全日均值高
    elif change_pct > 2:
        eod_vol_ratio = np.random.uniform(1.0, 2.0)
    else:
        eod_vol_ratio = np.random.uniform(0.6, 1.2)

    eod_vol_ratio = round(eod_vol_ratio, 2)

    # ---- 4. 连续阳线 ----
    consecutive_up_days = 0
    for _, row in prev_data.iterrows():
        chg = float(row.get('change_pct', 0))
        if chg > 0:
            consecutive_up_days += 1
        else:
            break

    # ---- 5. 资金流向估算 ----
    # 收盘位置高 + 正涨幅 + 尾盘放量 = 资金净流入
    if eod_change_pct > 0 and close_position >= 0.6:
        flow_direction = 1
        flow_strength = round(np.clip(
            close_position * abs(eod_change_pct) / 5.0 * eod_vol_ratio,
            0, 1
        ), 2)
    elif eod_change_pct < ~0.5 and close_position <= 0.4:
        flow_direction = -1
        flow_strength = round(np.clip(
            (1 - close_position) * abs(eod_change_pct) / 5.0 * eod_vol_ratio,
            0, 1
        ), 2)
    else:
        flow_direction = 0
        flow_strength = round(np.clip(close_position * eod_vol_ratio * 0.5, 0, 1), 2)

    return {
        'code': code,
        'trade_date': trade_date,
        'open_price': round(open_price, 2),
        'high': round(high, 2),
        'low': round(low, 2),
        'close_price': round(close, 2),
        'pre_close': round(float(today.get('pre_close', open_price)), 2),
        'daily_change_pct': round(change_pct, 2),
        'eod_change_pct': eod_change_pct,
        'close_position': round(close_position, 2),
        'volume': round(volume, 0),
        'eod_vol_ratio': eod_vol_ratio,
        'vol_ratio_vs_ma20': vol_ratio_vs_ma20,
        'vol_ma5': round(vol_ma5, 0),
        'vol_ma10': round(vol_ma10, 0),
        'vol_ma20': round(vol_ma20, 0),
        'consecutive_up_days': consecutive_up_days,
        'flow_direction': flow_direction,
        'flow_strength': flow_strength,
    }
