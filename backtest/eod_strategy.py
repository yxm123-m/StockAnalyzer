"""
尾盘狙击 Backtrader 策略 — 尾盘进, 第二天出
"""
import backtrader as bt


class EodSniperStrategy(bt.Strategy):
    """
    尾盘狙击策略

    入场: 基于尾盘评分 (eod_score), 在收盘前买入
    出场: 第二天收盘卖出, 或触发止损/止盈
    """
    params = (
        ('min_score', 50),
        ('max_positions', 5),
        ('position_pct', 0.20),
        ('hold_days', 1),          # 隔日卖出
        ('stop_loss', -0.03),      # 短线止损 -3%
        ('take_profit', 0.05),     # 短线止盈 +5%
    )

    def __init__(self):
        self.entry_bar = {}       # data._name -> bar index
        self.entry_price = {}     # data._name -> entry price

    def next(self):
        # ===== 出场逻辑 =====
        to_close = []
        for name in list(self.entry_bar.keys()):
            data = self.getdatabyname(name)
            if data is None:
                continue

            pos = self.getposition(data)
            if pos.size == 0:
                to_close.append(name)
                continue

            entry_price = self.entry_price[name]
            current_price = data.close[0]
            pnl_pct = (current_price - entry_price) / entry_price
            bars_held = len(self) - self.entry_bar[name]

            exit_signal = None

            # 止损
            if pnl_pct <= self.params.stop_loss:
                exit_signal = f"止损({pnl_pct:+.2%})"
            # 止盈
            elif pnl_pct >= self.params.take_profit:
                exit_signal = f"止盈({pnl_pct:+.2%})"
            # 隔日超时 (hold_days = 1 表示第二天收盘出)
            elif bars_held >= self.params.hold_days:
                exit_signal = f"隔日出({pnl_pct:+.2%})"

            if exit_signal:
                self.close(data=data)
                to_close.append(name)

        for name in to_close:
            self.entry_bar.pop(name, None)
            self.entry_price.pop(name, None)

        # ===== 入场逻辑 =====
        if len(self.entry_bar) >= self.params.max_positions:
            return

        for data in self.datas:
            if data._name in self.entry_bar:
                continue

            # 读取尾盘评分 (自定义line)
            score = data.eod_score[0]
            if score >= self.params.min_score:
                cash = self.broker.get_cash()
                cash_per_trade = cash * self.params.position_pct
                size = int(cash_per_trade / data.close[0] / 100) * 100

                if size >= 100:
                    self.buy(data=data, size=size)
                    self.entry_bar[data._name] = len(self)
                    self.entry_price[data._name] = data.close[0]

    def notify_trade(self, trade):
        if trade.isclosed:
            pass  # 交易完成时可记录日志
