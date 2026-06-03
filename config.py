"""
StockAnalyzer 全局配置
"""
import os

# 项目根目录
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

# 数据库配置
DB_DIR = os.path.join(ROOT_DIR, "db")
DB_PATH = os.path.join(DB_DIR, "stock_analyzer.db")
os.makedirs(DB_DIR, exist_ok=True)

# 数据缓存TTL（秒）
CACHE_TTL = {
    "stock_list": 86400,        # 股票列表: 1天
    "daily_kline": 86400,       # 日K线: 1天
    "call_auction": 3600,       # 集合竞价: 1小时 (当天有效)
    "index_daily": 3600,        # 指数: 1小时
}

# 集合竞价策略参数
STRATEGY_PARAMS = {
    "min_score": 50,            # 最低推荐分数
    "max_positions": 5,         # 最大持仓数
    "position_pct": 0.20,       # 单笔仓位比例
    "hold_days": 5,             # 默认持仓天数
    "stop_loss": -0.05,         # 止损 -5%
    "take_profit": 0.10,        # 止盈 +10%
}

# 交易费用
TRADE_FEES = {
    "commission_rate": 0.0003,  # 佣金 万三
    "min_commission": 5.0,      # 最低佣金 5元
    "stamp_tax_rate": 0.001,    # 印花税 千一 (卖出)
    "transfer_fee": 0.00002,    # 过户费 万0.2
}

# 风控参数
RISK_PARAMS = {
    "max_position_pct": 0.25,       # 单只股票最大仓位
    "max_total_positions": 5,       # 最大持仓数
    "max_daily_loss": -50000,       # 单日最大亏损
    "max_total_drawdown": -0.20,    # 最大总回撤
    "min_cash_reserve": 50000,      # 最低现金保留
}

# 股市交易时间
TRADING_HOURS = {
    "call_auction_start": "09:15",
    "call_auction_end": "09:25",
    "morning_start": "09:30",
    "morning_end": "11:30",
    "afternoon_start": "13:00",
    "afternoon_end": "15:00",
}

# 指数代码
INDEX_CODES = {
    "上证指数": "sh000001",
    "深证成指": "sz399001",
    "创业板指": "sz399006",
    "科创50": "sh000688",
}

# 免责声明（全局使用）
DISCLAIMER_TEXT = """
⚠️ **风险提示**: 本系统仅供学习演示用途，所有数据和推荐均不构成投资建议。
历史回测收益不代表未来表现。股市有风险，投资需谨慎。
"""
