"""
集合竞价分析页面 — 竞价指标展示 + 股票推荐 (前10, 排除科创板/创业板)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import pandas as pd
from datetime import datetime
from data.call_auction_fetcher import fetch_call_auction_data
from data.database import get_strategy_signals, get_all_stocks
from strategy.call_auction_scorer import score_all, grade_label
from common import show_disclaimer, plot_bar

st.set_page_config(page_title="集合竞价分析", page_icon="🔬", layout="wide")
show_disclaimer()

st.title("🔬 集合竞价分析")
st.caption("基于集合竞价量能、价格趋势、买卖失衡、跳空幅度四维评分模型，筛选潜在强势股")
st.caption("⚠️ 已排除科创板(688xxx)和创业板(300xxx)股票")

col1, col2, col3 = st.columns([1, 1, 2])
with col1:
    trade_date = st.date_input("分析日期", datetime.now())
with col2:
    max_stocks = st.selectbox("扫描范围", [50, 100, 200, 500], index=1)
with col3:
    st.markdown("<br>", unsafe_allow_html=True)
    scan_btn = st.button("🔍 开始扫描", type="primary", use_container_width=True)

if scan_btn:
    date_str = trade_date.strftime("%Y-%m-%d")
    st.markdown(f"### 📊 扫描中... (日期: {date_str}, 范围: {max_stocks}只)")

    with st.spinner("正在获取集合竞价数据..."):
        ca_data = fetch_call_auction_data(date_str, None, max_stocks)
        if ca_data is None or ca_data.empty:
            st.error("无法获取竞价数据。可能原因：非交易日、akshare接口异常")
            st.info("💡 提示：尝试在工作日运行，或减小扫描范围")
        else:
            st.success(f"已获取 {len(ca_data)} 只股票的竞价数据")
            with st.spinner("正在计算评分..."):
                records = ca_data.to_dict('records')
                stock_map = {s['code']: s['name'] for s in get_all_stocks()}
                for r in records:
                    r['name'] = stock_map.get(r['code'], r['code'])
                results = score_all(records, date_str)
            st.success(f"评分完成! 共分析 {len(results)} 只股票 (已排除科创板/创业板)")

            st.markdown("### 📊 分析概览")
            a_count = sum(1 for r in results if r['grade'] == 'A')
            b_count = sum(1 for r in results if r['grade'] == 'B')
            c_count = sum(1 for r in results if r['grade'] == 'C')
            d_count = sum(1 for r in results if r['grade'] == 'D')
            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("🟢 A级强推", a_count)
            m2.metric("🔵 B级推荐", b_count)
            m3.metric("🟡 C级关注", c_count)
            m4.metric("⚪ D级忽略", d_count)
            m5.metric("总计", len(results))

            st.markdown("### 🏆 推荐股票列表 (前10)")
            top_n = min(10, len(results))
            df_show = pd.DataFrame(results[:top_n])
            if not df_show.empty:
                cols = ['rank','code','name','total_score','grade',
                       'volume_score','trend_score','imbalance_score','gap_score','open_gap_pct']
                df_show = df_show[[c for c in cols if c in df_show.columns]]
                st.dataframe(df_show, use_container_width=True, hide_index=True)

            st.markdown("### 📊 分数分布")
            scores = [r['total_score'] for r in results]
            bins = [0, 35, 50, 70, 100]
            labels = ['D(0-35)', 'C(35-50)', 'B(50-70)', 'A(70-100)']
            hist_data = pd.cut(scores, bins=bins, labels=labels).value_counts().sort_index()
            st.plotly_chart(plot_bar(hist_data.index.tolist(), hist_data.values.tolist(),
                                     title="股票评分分布", xlabel="等级", ylabel="数量"),
                           use_container_width=True)

st.markdown("---")
st.markdown("### 📋 历史推荐信号")
if st.button("📂 加载最近信号"):
    signals = get_strategy_signals(limit=50)
    if signals:
        df_sig = pd.DataFrame(signals)
        st.dataframe(df_sig, use_container_width=True, hide_index=True)
    else:
        st.info("暂无历史信号，请先运行扫描")

st.markdown("---")
st.markdown("### 📖 评分模型说明")
st.markdown("""
| 维度 | 满分 | 评估内容 |
|------|------|---------|
| **量能得分** | 30分 | 竞价成交量相对于20日均量的倍数 |
| **趋势得分** | 25分 | 竞价期间价格走势的方向和稳定性 |
| **失衡得分** | 25分 | 竞价买卖盘的比例，买方占比越高越好 |
| **跳空得分** | 20分 | 开盘涨幅，2%-5%为最佳区间 |

**等级**: A(≥70) 强推 | B(50-69) 推荐 | C(35-49) 关注 | D(<35) 忽略
**范围**: 仅限主板 + 中小板，已排除科创板(688)和创业板(300/301)
""")
