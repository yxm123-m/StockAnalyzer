"""
模拟交易页面 — 虚拟账户 + 下单 + 持仓管理
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import pandas as pd
from datetime import datetime
from common import show_disclaimer, plot_pie
from data.database import get_paper_positions

st.set_page_config(page_title="模拟交易", page_icon="💼", layout="wide")
show_disclaimer()

st.title("💼 模拟交易")
st.caption("虚拟资金账户，验证策略实战效果")

from paper_trade.portfolio import Portfolio
from paper_trade.broker import Broker
from paper_trade.risk import RiskManager

if 'portfolio' not in st.session_state:
    st.session_state.portfolio = Portfolio()
    st.session_state.risk = RiskManager()
    st.session_state.broker = Broker(st.session_state.portfolio, st.session_state.risk)

portfolio = st.session_state.portfolio
risk_mgr = st.session_state.risk
broker = st.session_state.broker

# 账户概览
st.markdown("### 💰 账户概览")
data = portfolio.to_dict()
c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    st.metric("总资产", f"¥{data['total_value']:,.0f}")
with c2:
    st.metric("可用现金", f"¥{data['cash']:,.0f}")
with c3:
    st.metric("持仓市值", f"¥{data['market_value']:,.0f}")
with c4:
    st.metric("累计收益率", f"{data['total_return_pct']:+.2f}%")
with c5:
    st.metric("持仓数", f"{data['position_count']}/5")

# 下单
st.markdown("---")
st.markdown("### 📝 下单")
from data.database import get_strategy_signals
signals = get_strategy_signals(limit=10)
signal_options = ["— 手动输入 —"]
if signals:
    signal_options += [f"{s['code']} {s['name']} (评分{s['total_score']:.0f}, {s['grade']}级)" for s in signals]
selected = st.selectbox("📌 快速选择 (来自集合竞价推荐)", signal_options)
default_code = selected.split()[0] if selected != "— 手动输入 —" else ""

o1, o2, o3, o4 = st.columns([2, 2, 1, 2])
with o1:
    code = st.text_input("股票代码", default_code, placeholder="如: 000001")
with o2:
    name = st.text_input("股票名称", "", placeholder="自动或手动输入")
with o3:
    direction = st.radio("方向", ["BUY", "SELL"], horizontal=True)
with o4:
    price = st.number_input("价格", 0.01, 99999.99, 10.0, 0.01)
    shares = st.number_input("数量(股)", 100, 10000000, 100, 100)

if price > 0 and shares >= 100:
    order_val = price * shares
    comm = max(5.0, order_val * 0.0003)
    fee = order_val * 0.00002
    tax = order_val * 0.001 if direction == "SELL" else 0
    total = order_val + comm + fee + tax if direction == "BUY" else order_val - comm - fee - tax
    st.caption(f"订单金额: ¥{order_val:,.2f} | 佣金: ¥{comm:.2f} | {'支出' if direction=='BUY' else '收入'}: ¥{total:,.2f}")

reason = st.text_input("交易理由 (可选)")
if st.button("🔒 确认下单", type="primary"):
    if not code:
        st.error("请输入股票代码")
    elif shares < 100:
        st.error("最小交易单位为100股")
    else:
        success, msg = broker.place_order(code, name or code, direction, price, shares, reason)
        if success:
            st.success(msg)
            st.rerun()
        else:
            st.error(msg)

# 持仓
st.markdown("---")
st.markdown("### 📦 当前持仓")
positions = get_paper_positions()
if positions:
    st.dataframe(pd.DataFrame(positions), use_container_width=True, hide_index=True)
    close_col1, close_col2 = st.columns([3, 1])
    with close_col1:
        close_code = st.selectbox("选择持仓", [p['code'] for p in positions])
    with close_col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("全部卖出", type="secondary"):
            pos = portfolio.get_position(close_code)
            if pos:
                success, msg = broker.sell(close_code, pos['name'],
                                           pos['current_price'] or pos['avg_cost'],
                                           pos['shares'], "手动平仓")
                st.success(msg) if success else st.error(msg)
                if success:
                    st.rerun()
else:
    st.info("暂无持仓")

# 订单历史
st.markdown("---")
st.markdown("### 📜 订单历史")
orders = portfolio.get_orders(50)
if orders:
    st.dataframe(pd.DataFrame(orders), use_container_width=True, hide_index=True)
else:
    st.info("暂无订单记录")

# 持仓结构
if positions:
    st.markdown("---")
    st.markdown("### 📊 持仓结构")
    labels = [p['name'] for p in positions] + ["现金"]
    values = [p['market_value'] for p in positions] + [portfolio.cash]
    st.plotly_chart(plot_pie(labels, values, "资产分布"), use_container_width=True)

# 重置
st.markdown("---")
with st.expander("⚠️ 重置模拟账户", expanded=False):
    st.warning("重置将清空所有持仓和订单记录，恢复初始资金100万")
    if st.button("确认重置"):
        from data.database import get_conn
        conn = get_conn()
        conn.execute("DELETE FROM paper_positions")
        conn.execute("DELETE FROM paper_orders")
        conn.execute("UPDATE paper_account SET cash=1000000, commission=0, stamp_tax=0, updated_at=datetime('now','localtime')")
        conn.commit()
        conn.close()
        portfolio.refresh()
        st.success("账户已重置")
        st.rerun()
