"""
量化回测页面 — 集合竞价策略回测
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from ui.components.common import show_disclaimer, plot_equity_curve

st.set_page_config(page_title="量化回测", page_icon="⚡", layout="wide")
show_disclaimer()

st.title("⚡ 量化回测")
st.caption("基于集合竞价评分策略的历史数据回测")

# ---- 配置面板 ----
st.markdown("### ⚙️ 回测参数")

col1, col2, col3 = st.columns(3)

with col1:
    start_date = st.date_input("开始日期", datetime.now() - timedelta(days=365))
    end_date = st.date_input("结束日期", datetime.now())
    initial_cash = st.number_input("初始资金", 10000, 10000000, 100000, 10000, format="%d")

with col2:
    min_score = st.slider("最低评分阈值", 0, 100, 50, 5,
                          help="只有评分>=此值的股票才考虑买入")
    max_positions = st.slider("最大持仓数", 1, 20, 5)
    position_pct = st.slider("单笔仓位比例(%)", 5, 50, 20) / 100

with col3:
    hold_days = st.slider("持仓天数", 1, 30, 5,
                          help="超过此天数强制平仓")
    stop_loss = st.slider("止损(%)", -20, 0, -5, 1) / 100
    take_profit = st.slider("止盈(%)", 0, 50, 10, 1) / 100

# 股票池选择
st.markdown("### 📋 股票池")
pool_options = ["沪深300 (推荐)", "中证500", "全部A股(较慢)", "自定义代码"]
pool_choice = st.selectbox("选择股票池", pool_options, index=0)

custom_codes = ""
if pool_choice == "自定义代码":
    custom_codes = st.text_input("输入股票代码 (逗号分隔)", "000001,600036,000858")

# ---- 运行回测 ----
run_col1, run_col2 = st.columns([1, 3])
with run_col1:
    run_btn = st.button("▶ 开始回测", type="primary", use_container_width=True)

if run_btn:
    sd = start_date.strftime("%Y-%m-%d")
    ed = end_date.strftime("%Y-%m-%d")

    if start_date >= end_date:
        st.error("开始日期必须早于结束日期")
    else:
        # 获取股票列表
        codes = []
        if pool_choice == "沪深300 (推荐)":
            try:
                import akshare as ak
                df = ak.index_stock_cons_weight_csindex("000300")
                codes = df['成分券代码'].astype(str).str.strip().tolist()[:50]
            except Exception:
                from data.database import get_all_stocks
                codes = [s['code'] for s in get_all_stocks()[:50]]
        elif pool_choice == "中证500":
            try:
                import akshare as ak
                df = ak.index_stock_cons_weight_csindex("000905")
                codes = df['成分券代码'].astype(str).str.strip().tolist()[:50]
            except Exception:
                codes = []
        elif pool_choice == "自定义代码":
            codes = [c.strip() for c in custom_codes.split(",") if c.strip()]
        else:
            from data.database import get_all_stocks
            codes = [s['code'] for s in get_all_stocks()[:50]]

        if not codes:
            st.warning("未获取到股票代码，使用默认列表")
            codes = ["000001", "600036", "000858", "600519", "601318"]

        st.info(f"回测股票池: {len(codes)} 只 ({codes[:5]}...)")

        # 执行回测
        with st.spinner(f"回测运行中 ({sd} ~ {ed})..."):
            try:
                from backtest.engine import run_backtest
                metrics = run_backtest(
                    codes, sd, ed,
                    initial_cash=initial_cash, min_score=min_score,
                    max_positions=max_positions, position_pct=position_pct,
                    hold_days=hold_days, stop_loss=stop_loss,
                    take_profit=take_profit,
                )

                if 'error' in metrics:
                    st.error(metrics['error'])
                    st.info("💡 提示：请确保数据库中有足够的竞价数据。先在「集合竞价」页面运行扫描生成数据。")
                else:
                    st.success("回测完成!")

                    # ---- 结果展示 ----
                    st.markdown("### 📊 回测结果")

                    c1, c2, c3, c4 = st.columns(4)
                    with c1:
                        st.metric("总收益", f"{metrics['total_return']:+.2f}%",
                                  delta=f"¥{metrics['final_value'] - metrics['initial_value']:+,.0f}")
                    with c2:
                        st.metric("年化收益", f"{metrics['annual_return']:+.2f}%")
                    with c3:
                        st.metric("夏普比率", f"{metrics['sharpe_ratio']:.2f}")
                    with c4:
                        st.metric("最大回撤", f"{metrics['max_drawdown']:.2f}%",
                                  delta_color="inverse")

                    c5, c6, c7, c8 = st.columns(4)
                    with c5:
                        st.metric("胜率", f"{metrics['win_rate']:.1f}%")
                    with c6:
                        st.metric("交易次数", metrics['total_trades'])
                    with c7:
                        st.metric("初值", f"¥{metrics['initial_value']:,.0f}")
                    with c8:
                        st.metric("终值", f"¥{metrics['final_value']:,.0f}")

                    # 参数摘要
                    st.markdown(f"""
                    **回测参数**: 评分≥{min_score} | 持仓≤{max_positions}只 |
                    仓位{position_pct*100:.0f}% | 持有{hold_days}天 |
                    止损{stop_loss*100:.0f}% | 止盈{take_profit*100:.0f}%
                    """)

            except Exception as e:
                st.error(f"回测运行失败: {e}")
                st.info("💡 可能原因：数据不足、网络问题、或参数不合理。请先确保已在「集合竞价」页面生成数据。")

# ---- 历史回测记录 ----
st.markdown("---")
st.markdown("### 📜 历史回测记录")

try:
    from data.database import get_conn
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM backtest_runs ORDER BY created_at DESC LIMIT 10"
    ).fetchall()
    conn.close()

    if rows:
        df_hist = pd.DataFrame([dict(r) for r in rows])
        st.dataframe(df_hist[['run_name', 'start_date', 'end_date', 'total_return',
                               'sharpe_ratio', 'max_drawdown', 'win_rate',
                               'total_trades', 'created_at']],
                     use_container_width=True, hide_index=True)
    else:
        st.info("暂无回测记录")
except Exception:
    st.info("暂无回测记录")
