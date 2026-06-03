"""
回测绩效指标计算
"""
import math


def compute_metrics(strat, initial_cash, initial_value, final_value,
                    start_date, end_date):
    """从 backtrader 分析器提取绩效指标"""
    # 基本收益
    total_return = (final_value / initial_cash - 1) * 100

    # 年化收益
    from datetime import datetime
    try:
        sd = datetime.strptime(start_date, "%Y-%m-%d")
        ed = datetime.strptime(end_date, "%Y-%m-%d")
        years = max((ed - sd).days / 365.25, 0.1)
    except Exception:
        years = 1
    annual_return = ((final_value / initial_cash) ** (1 / years) - 1) * 100

    # 夏普比率
    sharpe = 0
    try:
        sharpe_analysis = strat.analyzers.sharpe.get_analysis()
        sharpe = sharpe_analysis.get('sharperatio', 0)
        if sharpe is None:
            sharpe = 0
    except Exception:
        pass

    # 最大回撤
    max_dd = 0
    try:
        dd_analysis = strat.analyzers.drawdown.get_analysis()
        max_dd = dd_analysis.get('max', {}).get('drawdown', 0) or 0
        if isinstance(max_dd, (int, float)):
            max_dd = max_dd * 100 if abs(max_dd) < 10 else max_dd
    except Exception:
        pass

    # 交易统计
    total_trades = 0
    win_count = 0
    lose_count = 0
    try:
        trade_analysis = strat.analyzers.trades.get_analysis()
        total_trades = trade_analysis.get('total', {}).get('total', 0)
        won = trade_analysis.get('won', {})
        lost = trade_analysis.get('lost', {})
        win_count = won.get('total', 0) if won else 0
        lose_count = lost.get('total', 0) if lost else 0
    except Exception:
        pass

    win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0

    return {
        'initial_value': initial_cash,
        'final_value': round(final_value, 2),
        'total_return': round(total_return, 2),
        'annual_return': round(annual_return, 2),
        'sharpe_ratio': round(sharpe, 2) if sharpe else 0,
        'max_drawdown': round(max_dd, 2),
        'win_rate': round(win_rate, 1),
        'total_trades': total_trades,
        'win_trades': win_count,
        'lose_trades': lose_count,
        'start_date': start_date,
        'end_date': end_date,
    }
