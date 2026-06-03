"""
纸交易账户管理
"""
from datetime import datetime
from data.database import (
    get_paper_account, update_paper_account,
    get_paper_positions, update_paper_position, delete_paper_position,
    save_paper_order, get_paper_orders
)


class Portfolio:
    """虚拟投资组合"""

    def __init__(self):
        self.refresh()

    def refresh(self):
        """从数据库刷新状态"""
        acct = get_paper_account()
        if acct:
            self.cash = acct['cash']
            self.initial_cash = acct['initial_cash']
            self.total_commission = acct['commission']
            self.total_stamp_tax = acct['stamp_tax']
        else:
            self.cash = 1_000_000
            self.initial_cash = 1_000_000
            self.total_commission = 0
            self.total_stamp_tax = 0

        self.positions = {p['code']: p for p in get_paper_positions()}

    @property
    def total_market_value(self):
        return sum(p.get('market_value', 0) for p in self.positions.values())

    @property
    def total_value(self):
        return self.cash + self.total_market_value

    @property
    def total_return_pct(self):
        return (self.total_value / self.initial_cash - 1) * 100 if self.initial_cash > 0 else 0

    @property
    def position_count(self):
        return len(self.positions)

    @property
    def daily_pnl(self):
        """今日盈亏（估算）"""
        return sum(p.get('unrealized_pnl', 0) for p in self.positions.values())

    def get_position(self, code):
        return self.positions.get(code)

    def has_position(self, code):
        return code in self.positions

    def get_position_value(self, code):
        pos = self.positions.get(code)
        return pos['market_value'] if pos else 0

    def execute_buy(self, code, name, price, shares, commission=0, reason=""):
        """执行买入"""
        cost = price * shares + commission
        if cost > self.cash:
            return False, "现金不足"

        self.cash -= cost
        self.total_commission += commission

        # 更新或创建持仓
        existing = self.positions.get(code)
        if existing:
            total_shares = existing['shares'] + shares
            avg_cost = ((existing['avg_cost'] * existing['shares']) +
                        (price * shares)) / total_shares
        else:
            total_shares = shares
            avg_cost = price

        update_paper_position(code, name, total_shares, avg_cost, price)
        update_paper_account(cash=self.cash, commission=self.total_commission)
        save_paper_order(code, name, 'BUY', price, shares, commission, 0, reason)

        self.refresh()
        return True, f"买入 {name} {shares}股 @ {price:.2f}"

    def execute_sell(self, code, price, shares, commission=0, stamp_tax=0, reason=""):
        """执行卖出"""
        pos = self.positions.get(code)
        if not pos or pos['shares'] < shares:
            return False, "持仓不足"

        proceeds = price * shares - commission - stamp_tax
        self.cash += proceeds
        self.total_commission += commission
        self.total_stamp_tax += stamp_tax

        name = pos['name']
        remaining = pos['shares'] - shares

        if remaining > 0:
            update_paper_position(code, name, remaining, pos['avg_cost'], price)
        else:
            delete_paper_position(code)

        update_paper_account(
            cash=self.cash, commission=self.total_commission,
            stamp_tax=self.total_stamp_tax
        )
        save_paper_order(code, name, 'SELL', price, shares, commission, stamp_tax, reason)

        self.refresh()
        return True, f"卖出 {name} {shares}股 @ {price:.2f}"

    def get_orders(self, limit=50):
        return get_paper_orders(limit)

    def to_dict(self):
        return {
            'cash': self.cash,
            'market_value': self.total_market_value,
            'total_value': self.total_value,
            'total_return_pct': self.total_return_pct,
            'initial_cash': self.initial_cash,
            'position_count': self.position_count,
            'daily_pnl': self.daily_pnl,
        }
