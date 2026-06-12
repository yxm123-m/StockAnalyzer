"""
StockAnalyzer — A股尾盘狙击系统
单页面：尾盘扫描 + 评分推荐
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import pandas as pd
from datetime import datetime
from data.database import init_db, get_all_stocks, get_strategy_signals
from data.eod_fetcher import fetch_eod_data
from strategy.eod_scorer import score_all
from common import show_disclaimer, plot_bar

st.set_page_config(
    page_title="A股尾盘狙击系统",
    page_icon="🎯",
    layout="wide",
)

init_db()

show_disclaimer()

st.title("🎯 尾盘狙击分析")
st.caption("基于尾盘动量、量能爆发、日线强势、资金流向四维评分模型")
st.caption("⚠️ 已排除科创板(688xxx)和创业板(300xxx/301xxx)")
st.caption("🕐 最佳扫描时间: 14:30-14:55 (尾盘最后30分钟)")

col1, col2, col3, col4 = st.columns([1, 1, 1, 2])
with col1:
    trade_date = st.date_input("分析日期", datetime.now())
with col2:
    max_stocks = st.selectbox("扫描范围", [50, 100, 200, 500], index=1)
with col3:
    st.markdown("<br>", unsafe_allow_html=True)
    scan_btn = st.button("🔍 开始扫描", type="primary", use_container_width=True)

if scan_btn:
    date_str = trade_date.strftime("%Y-%m-%d")
    st.markdown(f"### 📊 扫描中... ({date_str}, {max_stocks}只)")

    with st.spinner("获取尾盘数据..."):
        eod_data = fetch_eod_data(date_str, None, max_stocks)
        if eod_data is None or eod_data.empty:
            st.error("无法获取尾盘数据（非交易日或接口异常）")
        else:
            st.success(f"获取 {len(eod_data)} 只股票")

            with st.spinner("评分中..."):
                records = eod_data.to_dict('records')
                name_map = {s['code']: s['name'] for s in get_all_stocks()}
                for r in records:
                    r['name'] = name_map.get(r['code'], r['code'])
                results = score_all(records, date_str)

            st.success(f"完成! {len(results)} 只 (排除科创板/创业板)")

            # 概览
            st.markdown("### 📊 概览")
            a = sum(1 for r in results if r['grade'] == 'A')
            b = sum(1 for r in results if r['grade'] == 'B')
            c = sum(1 for r in results if r['grade'] == 'C')
            d = sum(1 for r in results if r['grade'] == 'D')
            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("🟢 A级强推", a)
            m2.metric("🔵 B级推荐", b)
            m3.metric("🟡 C级关注", c)
            m4.metric("⚪ D级忽略", d)
            m5.metric("总计", len(results))

            # 推荐
            st.markdown("### 🏆 推荐股票 (前15)")
            top_n = min(15, len(results))
            df_show = pd.DataFrame(results[:top_n])
            if not df_show.empty:
                cols = ['rank','code','name','total_score','grade',
                       'momentum_score','volume_score','strength_score','flow_score',
                       'close_price','daily_change_pct','eod_change_pct']
                df_show = df_show[[c for c in cols if c in df_show.columns]]
                st.dataframe(df_show, use_container_width=True, hide_index=True)

            # 分布
            st.markdown("### 📊 分数分布")
            scores = [r['total_score'] for r in results]
            bins = [0, 35, 50, 70, 100]
            labels = ['D(0-35)', 'C(35-50)', 'B(50-70)', 'A(70-100)']
            hist = pd.cut(scores, bins=bins, labels=labels).value_counts().sort_index()
            st.plotly_chart(plot_bar(hist.index.tolist(), hist.values.tolist(),
                                     title="评分分布", xlabel="等级", ylabel="数量"),
                           use_container_width=True)

# 历史
st.markdown("---")
st.markdown("### 📋 历史信号")
if st.button("📂 加载最近信号"):
    signals = get_strategy_signals(limit=50)
    if signals:
        st.dataframe(pd.DataFrame(signals), use_container_width=True, hide_index=True)
    else:
        st.info("暂无历史信号")

# 模型说明
st.markdown("---")
st.markdown("### 📖 评分模型")
st.markdown("""
| 维度 | 满分 | 评估 |
|------|------|------|
| **尾盘动量** | 30分 | 最后30分钟涨跌幅 + 收盘在日内区间的位置 |
| **量能爆发** | 25分 | 尾盘放量倍数 + 全日量 vs 20日均量 |
| **日线强势** | 25分 | 当日涨跌幅 + 连续阳线天数 |
| **资金流向** | 20分 | 尾盘主动买盘方向与强度 |

**等级**: A(≥70) 强推 | B(50-69) 推荐 | C(35-49) 关注 | D(<35) 忽略
**策略**: 14:55尾盘买入 → T+1次日盘中择机卖出
""")
