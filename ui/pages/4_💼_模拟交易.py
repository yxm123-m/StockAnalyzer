"""
模拟交易页面 — 虚拟账户 + 下单 + 持仓管理
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
import pandas as pd
from datetime import datetime
from ui.components.common import show_disclaimer, plot_pie, plot_equity_curve

st.set_page_config(page_title="模拟交易", page_icon="💼", layout="wide")
show_disclaimer()

st.title("💼 模拟交易")
st.caption("虚拟资金账户，验证策略实战效果")

# 初始化
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

# ---- 账户概览 ----
st.markdown("### 💰 账户概览")
data = portfolio.to_dict()

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric("总资产", f"¥{data['total_value']:,.0f}")
with col2:
    st.metric("可用现金", f"¥{data['cash']:,.0f}")
with col3:
    st.metric("持仓市值", f"¥{data['market_value']:,.0f}")
with col4:
    total_ret = data['total_return_pct']
    st.metric("累计收益率", f"{total_ret:+.2f}%",
              delta_color="normal" if total_ret >= 0 else "inverse")
with col5:
    st.metric("持仓数", f"{data['position_count']}/5")

# ---- 风控状态 ----
with st.expander("🛡️ 风控状态", expanded=False):
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("单日盈亏", f"¥{data['daily_pnl']:+,.0f}")
        st.metric("最大回撤限制", f"{risk_mgr.params['max_total_drawdown']*100:.0f}%")
    with c2:
        st.metric("单只仓位上限", f"{risk_mgr.params['max_position_pct']*100:.0f}%")
        st.metric("单日亏损上限", f"¥{abs(risk_mgr.params['max_daily_loss']):,}")
    with c3:
        st.metric("最低现金保留", f"¥{risk_mgr.params['min_cash_reserve']:,}")
        st.metric("佣金费率", f"{risk_mgr.params.get('commission_rate', 0.0003)*10000:.0f}‱")

# ---- 下单区域 ----
st.markdown("---")
st.markdown("### 📝 下单")

from data.database import get_strategy_signals

# 加载推荐信号作为快捷下单参考
signals = get_strategy_signals(limit=10)
signal_options = ["— 手动输入 —"]
if signals:
    signal_options += [f"{s['code']} {s['name']} (评分{s['total_score']:.0f}, {s['grade']}级)" for s in signals]

selected_signal = st.selectbox("📌 快速选择 (来自集合竞价推荐)", signal_options)

if selected_signal != "— 手动输入 —":
    parts = selected_signal.split()
    default_code = parts[0]
    default_name = parts[1]
else:
    default_code = ""
    default_name = ""

order_col1, order_col2, order_col3, order_col4 = st.columns([2, 2, 1, 2])

with order_col1:
    code = st.text_input("股票代码", default_code, placeholder="如: 000001")
with order_col2:
    name = st.text_input("股票名称", default_name, placeholder="自动或手动输入")
with order_col3:
    direction = st.radio("方向", ["BUY", "SELL"], horizontal=True)
with order_col4:
    price = st.number_input("价格", 0.01, 99999.99, 10.0, 0.01, format="%.2f")
    shares = st.number_input("数量(股)", 100, 10000000, 100, 100,
                             help="A股最小交易单位100股")

# 费用预估
if price > 0 and shares >= 100:
    order_val = price * shares
    comm = max(5.0, order_val * 0.0003)
    fee = order_val * 0.00002
    tax = order_val * 0.001 if direction == "SELL" else 0
    total = order_val + comm + fee + tax if direction == "BUY" else order_val - comm - fee - tax
    st.caption(f"订单金额: ¥{order_val:,.2f} | 佣金: ¥{comm:.2f} | 过户费: ¥{fee:.2f} | "
               f"印花税: ¥{tax:.2f} | {'支出' if direction == 'BUY' else '收入'}: ¥{total:,.2f}")

reason = st.text_input("交易理由 (可选)", placeholder="如: 竞价信号A级推荐")

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

# ---- 持仓列表 ----
st.markdown("---")
st.markdown("### 📦 当前持仓")

positions = portfolio.get_paper_positions()
if positions:
    df_pos = pd.DataFrame(positions)
    st.dataframe(df_pos, use_container_width=True, hide_index=True,
                 column_config={
                     'avg_cost': st.column_config.NumberColumn('成本', format='%.2f'),
                     'current_price': st.column_config.NumberColumn('现价', format='%.2f'),
                     'market_value': st.column_config.NumberColumn('市值', format='¥%.0f'),
                     'unrealized_pnl': st.column_config.NumberColumn('浮动盈亏', format='¥%.0f'),
                 })

    # 快速平仓
    st.markdown("#### 🔒 快速平仓")
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
                if success:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
else:
    st.info("暂无持仓，请下单买入")

# ---- 订单历史 ----
st.markdown("---")
st.markdown("### 📜 订单历史")

orders = portfolio.get_orders(50)
if orders:
    df_ord = pd.DataFrame(orders)
    cols = [c for c in ['created_at', 'code', 'name', 'direction', 'price', 'shares',
                         'commission', 'stamp_tax', 'reason'] if c in df_ord.columns]
    st.dataframe(df_ord[cols], use_container_width=True, hide_index=True,
                 column_config={
                     'price': st.column_config.NumberColumn('价格', format='%.2f'),
                     'commission': st.column_config.NumberColumn('佣金', format='%.2f'),
                 })
else:
    st.info("暂无订单记录")

# ---- 持仓结构图 ----
if positions:
    st.markdown("---")
    st.markdown("### 📊 持仓结构")
    labels = [p['name'] for p in positions]
    values = [p['market_value'] for p in positions]
    # 加入现金
    labels.append("现金")
    values.append(portfolio.cash)

    fig = plot_pie(labels, values, "资产分布")
    st.plotly_chart(fig, use_container_width=True)

# ---- 重置账户 ----
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
