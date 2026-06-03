"""
风控模块 — 仓位、止损、回撤限制
"""
from config import RISK_PARAMS


class RiskManager:
    """风险控制管理器"""

    def __init__(self, params=None):
        self.params = params or RISK_PARAMS

    def check_order(self, portfolio, code, direction, price, shares):
        """
        订单风控检查
        返回: (allowed: bool, reason: str, adjusted_shares: int)
        """
        # 1. 总回撤限制
        if portfolio.total_return_pct <= self.params['max_total_drawdown'] * 100:
            return False, f"总回撤已达{self.params['max_total_drawdown']*100}%，停止交易", 0

        # 2. 单日亏损限制
        if portfolio.daily_pnl <= self.params['max_daily_loss']:
            return False, f"今日亏损已达{abs(self.params['max_daily_loss'])}元限制", 0

        order_value = price * shares

        if direction == 'BUY':
            # 3. 持仓集中度
            total_value = portfolio.total_value
            existing_value = portfolio.get_position_value(code)
            new_total = existing_value + order_value
            if new_total > total_value * self.params['max_position_pct']:
                max_add = total_value * self.params['max_position_pct'] - existing_value
                if max_add <= 0:
                    return False, f"{code}持仓超{self.params['max_position_pct']*100}%", 0
                adjusted = int(max_add / price / 100) * 100
                if adjusted < 100:
                    return False, "超出持仓集中度限制", 0
                return True, f"调整至{adjusted}股", adjusted

            # 4. 最大持仓数
            if not portfolio.has_position(code):
                if portfolio.position_count >= self.params['max_total_positions']:
                    return False, f"持仓数已达{self.params['max_total_positions']}", 0

            # 5. 资金充足性
            estimated_cost = order_value * 1.0015  # 含交易成本
            available = portfolio.cash - self.params['min_cash_reserve']
            if estimated_cost > available:
                max_affordable = int(available / (price * 1.0015) / 100) * 100
                if max_affordable < 100:
                    return False, "可用资金不足", 0
                return True, f"资金不足，调整至{max_affordable}股", max_affordable

        else:  # SELL
            # 6. 持仓检查
            pos = portfolio.get_position(code)
            if not pos or pos['shares'] < shares:
                held = pos['shares'] if pos else 0
                return False, f"持仓不足(持有{held}股)", 0

        return True, "OK", shares
