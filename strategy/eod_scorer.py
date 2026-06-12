"""
尾盘狙击评分引擎 — 核心算法

四维评分模型 (总分100):
  1. 尾盘动量 (0-30): 最后30分钟涨跌幅 + 收盘力度
  2. 量能爆发 (0-25): 尾盘量能 vs 全日均量
  3. 日线强势 (0-25): 当日整体涨幅 + 价格位置
  4. 资金流向 (0-20): 尾盘资金净流入估算
"""
import numpy as np
from datetime import datetime
from data.database import save_strategy_signals


def score_all(stocks_data, trade_date=None):
    """
    批量评分, 返回排序后的推荐列表
    stocks_data: list of dicts (from eod_fetcher or database)
    """
    if trade_date is None:
        trade_date = datetime.now().strftime("%Y-%m-%d")

    # 排除科创板(688xxx)和创业板(300xxx/301xxx)
    EXCLUDED_PREFIXES = ('688', '300', '301')

    results = []
    for s in stocks_data:
        try:
            code = s.get('code', '')
            if code.startswith(EXCLUDED_PREFIXES):
                continue

            total, subscores = compute_total_score(s)
            grade = _classify(total)

            results.append({
                'code': code,
                'name': s.get('name', ''),
                'trade_date': trade_date,
                'momentum_score': subscores['momentum'],
                'volume_score': subscores['volume'],
                'strength_score': subscores['strength'],
                'flow_score': subscores['flow'],
                'total_score': total,
                'grade': grade,
                'close_price': s.get('close_price', 0),
                'daily_change_pct': s.get('daily_change_pct', 0),
                'eod_change_pct': s.get('eod_change_pct', 0),
            })
        except Exception:
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
    momentum = score_eod_momentum(stock)
    volume = score_eod_volume(stock)
    strength = score_daily_strength(stock)
    flow = score_fund_flow(stock)

    total = momentum + volume + strength + flow
    subscores = {
        'momentum': momentum,
        'volume': volume,
        'strength': strength,
        'flow': flow,
    }
    return round(total, 1), subscores


# ===================== 维度1: 尾盘动量 (0-30) =====================

def score_eod_momentum(stock):
    """
    尾盘动量评分: 评估最后30分钟的拉升力度

    eod_change_pct: 尾盘30分钟涨跌幅
    close_position: 收盘价在日内高低区间的相对位置 (0-1)
    """
    eod_change = stock.get('eod_change_pct', 0)
    close_position = stock.get('close_position', 0.5)

    if eod_change is None:
        eod_change = 0
    if close_position is None:
        close_position = 0.5

    score = 0

    # 尾盘涨跌幅评分
    if eod_change >= 3.0:
        score += 15
    elif eod_change >= 2.0:
        score += 12
    elif eod_change >= 1.0:
        score += 8
    elif eod_change >= 0.5:
        score += 5
    elif eod_change >= 0.1:
        score += 2
    elif eod_change >= -0.5:
        score += 1

    # 收盘价位置评分 (越接近日内高越好)
    if close_position >= 0.8:
        score += 15
    elif close_position >= 0.65:
        score += 10
    elif close_position >= 0.5:
        score += 6
    elif close_position >= 0.35:
        score += 3
    elif close_position >= 0.2:
        score += 1

    return min(score, 30)


# ===================== 维度2: 量能爆发 (0-25) =====================

def score_eod_volume(stock):
    """
    尾盘量能评分: 尾盘成交量是否显著放大

    eod_vol_ratio: 尾盘量 / 全日均量(每30分钟)
    vol_ratio_vs_ma20: 全日量 vs 20日均量
    """
    eod_vol = stock.get('eod_vol_ratio', 1.0)
    daily_vol = stock.get('vol_ratio_vs_ma20', 1.0)

    if eod_vol is None:
        eod_vol = 1.0
    if daily_vol is None:
        daily_vol = 1.0

    score = 0

    # 尾盘量能倍数 (相对于全日每30分钟均量)
    if eod_vol >= 3.0:
        score += 15
    elif eod_vol >= 2.0:
        score += 12
    elif eod_vol >= 1.5:
        score += 8
    elif eod_vol >= 1.2:
        score += 4
    elif eod_vol >= 1.0:
        score += 2

    # 全日放量加分
    if daily_vol >= 2.0:
        score += 10
    elif daily_vol >= 1.5:
        score += 7
    elif daily_vol >= 1.2:
        score += 4
    elif daily_vol >= 1.0:
        score += 2

    return min(score, 25)


# ===================== 维度3: 日线强势 (0-25) =====================

def score_daily_strength(stock):
    """
    日线强势评分: 当日整体表现

    daily_change_pct: 当日涨跌幅
    需要排除涨停板(买入不了)和跌停板(太弱)
    """
    change = stock.get('daily_change_pct', 0)
    if change is None:
        change = 0

    # 涨停/跌停排除 (在pre_filter中处理, 这里只评分)
    score = 0

    if 3.0 <= change < 9.8:
        score += 15
    elif 2.0 <= change < 3.0:
        score += 12
    elif 1.0 <= change < 2.0:
        score += 8
    elif 0.5 <= change < 1.0:
        score += 5
    elif 0 <= change < 0.5:
        score += 2
    elif -1.0 <= change < 0:
        score += 3  # 微跌可能是机会
    elif -3.0 <= change < -1.0:
        score += 1
    # 跌超3%不加分

    # 连续阳线加分
    consecutive_up = stock.get('consecutive_up_days', 0)
    if consecutive_up is None:
        consecutive_up = 0

    if 1 <= consecutive_up <= 3:
        score += 10
    elif 4 <= consecutive_up <= 5:
        score += 5  # 有一定持续性但不过热
    elif consecutive_up > 5:
        score += 1  # 已涨太多

    return min(score, 25)


# ===================== 维度4: 资金流向 (0-20) =====================

def score_fund_flow(stock):
    """
    尾盘资金流向评分

    flow_direction: 1=流入, 0=平衡, -1=流出
    flow_strength: 尾盘主动买盘估算
    """
    direction = stock.get('flow_direction', 0)
    strength = stock.get('flow_strength', 0)

    if direction is None:
        direction = 0
    if strength is None:
        strength = 0

    score = 0

    # 方向分
    if direction == 1:
        score += 8
    elif direction == 0:
        score += 3

    # 强度分 (尾盘拉升 + 放量 = 资金流入信号)
    if strength >= 0.8:
        score += 12
    elif strength >= 0.6:
        score += 9
    elif strength >= 0.4:
        score += 6
    elif strength >= 0.2:
        score += 3
    elif strength > 0:
        score += 1

    return min(score, 20)


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
    labels = {
        'A': '🟢 强推',
        'B': '🔵 推荐',
        'C': '🟡 关注',
        'D': '⚪ 忽略',
    }
    return labels.get(grade, grade)
