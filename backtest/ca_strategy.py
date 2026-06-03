"""
集合竞价 Backtrader 策略
"""
import backtrader as bt


class CallAuctionStrategy(bt.Strategy):
    """
    基于集合竞价评分的交易策略

    入场条件: 当日竞价评分 >= min_score
    出场条件: 止损 / 止盈 / 持仓超时
    """
    params = (
        ('min_score', 50),
        ('max_positions', 5),
        ('position_pct', 0.20),
        ('hold_days', 5),
        ('stop_loss', -0.05),
        ('take_profit', 0.10),
    )

    def __init__(self):
        self.entry_bar = {}    # data._name -> bar index
        self.entry_price = {}  # data._name -> entry price

    def next(self):
        # 检查出场条件
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

            # 止损
            if pnl_pct <= self.params.stop_loss:
                self.close(data=data)
                to_close.append(name)
            # 止盈
            elif pnl_pct >= self.params.take_profit:
                self.close(data=data)
                to_close.append(name)
            # 超时
            elif bars_held >= self.params.hold_days:
                self.close(data=data)
                to_close.append(name)

        for name in to_close:
            self.entry_bar.pop(name, None)
            self.entry_price.pop(name, None)

        # 检查入场条件
        if len(self.entry_bar) >= self.params.max_positions:
            return

        for data in self.datas:
            if data._name in self.entry_bar:
                continue

            score = data.auction_score[0]
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
            pass  # 交易完成时可选记录日志
