"""
回测引擎 — Backtrader Cerebro 配置与执行
"""
import backtrader as bt

from backtest.ca_strategy import CallAuctionStrategy
from backtest.data_adapter import ASharePandasData, prepare_backtest_data
from backtest.metrics import compute_metrics


def run_backtest(stock_codes, start_date, end_date,
                 initial_cash=100000, min_score=50, max_positions=5,
                 position_pct=0.20, hold_days=5, stop_loss=-0.05,
                 take_profit=0.10, progress_callback=None):
    """
    运行回测

    参数:
        stock_codes: list of str, 股票代码列表
        start_date: str, 'YYYY-MM-DD'
        end_date: str, 'YYYY-MM-DD'
        ...其他策略参数

    返回:
        dict: {
            'final_value', 'total_return', 'annual_return',
            'sharpe_ratio', 'max_drawdown', 'win_rate', 'total_trades',
            'equity_curve': pd.DataFrame, 'trades': list
        }
    """
    cerebro = bt.Cerebro()

    # 策略
    cerebro.addstrategy(
        CallAuctionStrategy,
        min_score=min_score,
        max_positions=max_positions,
        position_pct=position_pct,
        hold_days=hold_days,
        stop_loss=stop_loss,
        take_profit=take_profit,
    )

    # 加载数据
    loaded = 0
    for code in stock_codes:
        df = prepare_backtest_data(code, start_date, end_date)
        if df is None or len(df) < 50:
            continue

        data = ASharePandasData(dataname=df)
        cerebro.adddata(data, name=code)
        loaded += 1

        if loaded >= 50:  # 限制加载数量
            break

        if progress_callback:
            progress_callback(loaded, len(stock_codes))

    if loaded == 0:
        return {'error': '没有可用的回测数据'}

    # 初始资金
    cerebro.broker.setcash(initial_cash)

    # 交易费用 (A股万三佣金 + 千一印花税)
    cerebro.broker.setcommission(commission=0.0003)

    # 分析器
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe', riskfreerate=0.02)
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')

    # 添加观察器 (用于获取权益曲线)
    cerebro.addobserver(bt.observers.Value)
    cerebro.addobserver(bt.observers.DrawDown)

    # 运行
    print(f"回测开始: {start_date} ~ {end_date}, {loaded}只股票, 初始资金{initial_cash:,.0f}")
    initial = cerebro.broker.getvalue()
    results = cerebro.run()
    final = cerebro.broker.getvalue()

    if not results:
        return {'error': '回测运行失败'}

    strat = results[0]

    # 提取指标
    metrics = compute_metrics(
        strat, initial_cash, initial, final,
        start_date, end_date
    )
    metrics['loaded_stocks'] = loaded

    return metrics
