"""
集合竞价评分引擎 — 核心算法

四维评分模型 (总分100):
  1. 量能得分 (0-30): 竞价量 vs 历史量均线
  2. 趋势得分 (0-25): 竞价价格走势 (斜率 + R²)
  3. 失衡得分 (0-25): 买卖盘比例
  4. 跳空得分 (0-20): 开盘涨幅是否在最佳区间
"""
import numpy as np
from datetime import datetime
from data.database import save_strategy_signals


def score_all(stocks_data, trade_date=None):
    """
    批量评分, 返回排序后的推荐列表
    stocks_data: list of dicts (from call_auction_fetcher or database)
    """
    if trade_date is None:
        trade_date = datetime.now().strftime("%Y-%m-%d")

    # 科创板(688xxx)和创业板(300xxx/301xxx)代码前缀黑名单
    EXCLUDED_PREFIXES = ('688', '300', '301')

    results = []
    for s in stocks_data:
        try:
            code = s.get('code', '')
            # 排除科创板和创业板
            if code.startswith(EXCLUDED_PREFIXES):
                continue

            total, subscores = compute_total_score(s)
            grade = _classify(total)

            results.append({
                'code': code,
                'name': s.get('name', ''),
                'trade_date': trade_date,
                'volume_score': subscores['volume'],
                'trend_score': subscores['trend'],
                'imbalance_score': subscores['imbalance'],
                'gap_score': subscores['gap'],
                'total_score': total,
                'grade': grade,
                'open_gap_pct': s.get('open_gap_pct', 0),
                'auction_volume': s.get('auction_volume', 0),
            })
        except Exception as e:
            continue

    # 排序
    results.sort(key=lambda x: x['total_score'], reverse=True)

    # 排名
    for i, r in enumerate(results):
        r['rank'] = i + 1

    # 缓存到数据库
    if results:
        try:
            save_strategy_signals(results)
        except Exception:
            pass

    return results


def compute_total_score(stock):
    """计算单只股票的综合得分"""
    vol = score_volume_surge(stock)
    trend = score_price_trend(stock)
    imbalance = score_imbalance(stock)
    gap = score_gap(stock)

    total = vol + trend + imbalance + gap
    subscores = {'volume': vol, 'trend': trend, 'imbalance': imbalance, 'gap': gap}
    return round(total, 1), subscores


# ===================== 维度1: 量能 (0-30) =====================

def score_volume_surge(stock):
    """竞价量能评分"""
    vol_ratio = stock.get('vol_ratio_vs_ma20', 1)
    if vol_ratio is None or vol_ratio <= 0:
        return 0

    # 竞价量相对于20日均量的倍数
    if vol_ratio >= 3.0:
        return 30
    elif vol_ratio >= 2.0:
        return 22
    elif vol_ratio >= 1.5:
        return 15
    elif vol_ratio >= 1.2:
        return 8
    elif vol_ratio >= 1.0:
        return 3
    else:
        return 0


# ===================== 维度2: 价格趋势 (0-25) =====================

def score_price_trend(stock):
    """竞价价格趋势评分"""
    # 使用 price_trend_slope 和 open_gap_pct 综合判断
    slope = stock.get('price_trend_slope', 0)
    gap = stock.get('open_gap_pct', 0)

    if gap is None:
        gap = 0
    if slope is None:
        slope = 0

    # 正向跳空 + 正向趋势 = 高分
    score = 0

    # gap信号
    if gap > 3:
        score += 12
    elif gap > 1.5:
        score += 8
    elif gap > 0.5:
        score += 4
    elif gap > 0:
        score += 2

    # 趋势信号 (slope衡量竞价期间价格是否持续走高)
    if slope > 0.01:
        score += 13
    elif slope > 0.005:
        score += 8
    elif slope > 0.001:
        score += 4
    elif slope > -0.001:
        score += 3
    # 负斜率不加分

    return min(score, 25)


# ===================== 维度3: 买卖失衡 (0-25) =====================

def score_imbalance(stock):
    """买卖失衡评分"""
    ratio = stock.get('imbalance_ratio', 0.5)
    if ratio is None:
        return 0

    # ratio = bid_vol / (bid_vol + ask_vol)
    if ratio >= 0.85:
        return 25
    elif ratio >= 0.75:
        return 20
    elif ratio >= 0.65:
        return 15
    elif ratio >= 0.58:
        return 10
    elif ratio >= 0.53:
        return 5
    elif ratio >= 0.50:
        return 3
    else:
        return 0


# ===================== 维度4: 跳空幅度 (0-20) =====================

def score_gap(stock):
    """开盘跳空幅度评分"""
    gap = stock.get('open_gap_pct', 0)
    if gap is None:
        return 0

    # 最佳区间: 2%-5% (有强度但不至于追高)
    if 2.0 <= gap <= 5.0:
        deviation = abs(gap - 3.5)  # 3.5%为峰值
        return max(0, round(20 * (1 - deviation / 5.0), 1))
    elif 1.0 <= gap < 2.0:
        return 8
    elif 5.0 < gap <= 7.0:
        return 8
    elif 0 <= gap < 1.0:
        return 3
    elif 7.0 < gap <= 9.0:
        return 3
    else:
        return 0


# ===================== 等级分类 =====================

def _classify(total_score):
    if total_score >= 70:
        return 'A'  # 强推
    elif total_score >= 50:
        return 'B'  # 推荐
    elif total_score >= 35:
        return 'C'  # 关注
    else:
        return 'D'  # 忽略


def grade_label(grade):
    labels = {'A': '🟢 强推', 'B': '🔵 推荐', 'C': '🟡 关注', 'D': '⚪ 忽略'}
    return labels.get(grade, grade)
