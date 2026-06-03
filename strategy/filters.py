"""
前置过滤器 — 排除不适合分析的股票
"""

def pre_filter(stock_info, daily_data=None):
    """
    前置过滤, 返回 (pass: bool, reason: str)
    stock_info: dict with code, name, is_st, listed_date, etc.
    daily_data: DataFrame of recent kline data (optional)
    """
    # 1. 排除ST股票
    if stock_info.get('is_st'):
        return False, "ST股票"

    # 2. 排除上市不足60天的股票
    listed_date = stock_info.get('listed_date')
    if listed_date:
        from datetime import datetime, timedelta
        try:
            ld = datetime.strptime(str(listed_date)[:10], "%Y-%m-%d")
            if (datetime.now() - ld).days < 60:
                return False, "上市不足60日"
        except Exception:
            pass

    # 3. 排除前一日涨跌停的股票
    if daily_data is not None and len(daily_data) >= 1:
        prev = daily_data.iloc[-1]
        prev_change = prev.get('change_pct', 0)
        if abs(prev_change) >= 9.8:
            return False, f"前日涨跌停({prev_change:+.1f}%)"

    return True, "OK"


def filter_stocks(stock_list, daily_cache=None):
    """
    批量过滤, 返回通过过滤的股票列表
    stock_list: list of dicts
    """
    passed = []
    filtered = []
    for s in stock_list:
        ok, reason = pre_filter(s, daily_cache.get(s['code']) if daily_cache else None)
        if ok:
            passed.append(s)
        else:
            filtered.append((s['code'], s.get('name', ''), reason))
    return passed, filtered
