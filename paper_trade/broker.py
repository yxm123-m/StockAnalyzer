"""
订单撮合引擎 — 模拟市场订单执行
"""
from datetime import datetime


class Broker:
    """简单的模拟券商"""

    def __init__(self, portfolio, risk_manager=None):
        self.portfolio = portfolio
        self.risk_manager = risk_manager

    def place_order(self, code, name, direction, price, shares, reason=""):
        """
        下单 (市价单/限价单简化为直接成交)
        返回: (success: bool, message: str)
        """
        if shares < 100:
            return False, "最小交易单位为100股"

        if direction not in ('BUY', 'SELL'):
            return False, "方向必须为BUY或SELL"

        # 风控检查
        if self.risk_manager:
            allowed, msg, adjusted = self.risk_manager.check_order(
                self.portfolio, code, direction, price, shares
            )
            if not allowed:
                return False, msg
            if adjusted != shares:
                shares = adjusted

        # 计算费用
        order_value = price * shares
        commission = max(5.0, order_value * 0.0003)  # 万三, 最低5元

        if direction == 'BUY':
            stamp_tax = 0
            transfer_fee = order_value * 0.00002
            total_cost = order_value + commission + transfer_fee

            if total_cost > self.portfolio.cash:
                return False, f"资金不足 (需{total_cost:,.0f}, 可用{self.portfolio.cash:,.0f})"

            success, msg = self.portfolio.execute_buy(
                code, name, price, shares, commission + transfer_fee, reason
            )
            return success, msg

        else:  # SELL
            stamp_tax = order_value * 0.001  # 千一印花税
            transfer_fee = order_value * 0.00002

            success, msg = self.portfolio.execute_sell(
                code, price, shares, commission + transfer_fee, stamp_tax, reason
            )
            return success, msg

    def buy(self, code, name, price, shares, reason=""):
        return self.place_order(code, name, 'BUY', price, shares, reason)

    def sell(self, code, name, price, shares, reason=""):
        return self.place_order(code, name, 'SELL', price, shares, reason)
