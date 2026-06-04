"""
StockAnalyzer — A股集合竞价分析系统
Streamlit Cloud 入口文件
"""
import sys
import os

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
from data.database import init_db
from common import show_header, show_disclaimer

# 页面配置 — 必须是第一个 Streamlit 命令
st.set_page_config(
    page_title="A股集合竞价分析系统",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 初始化数据库
init_db()

# ---- 侧边栏 ----
with st.sidebar:
    st.markdown("# 📊 StockAnalyzer")
    st.markdown("### A股集合竞价分析系统")
    st.markdown("---")

    st.markdown("""
    **功能导航**:
    - 📈 **市场看板** — 指数、板块、涨跌榜
    - 🔬 **集合竞价** — 竞价分析 + 股票推荐
    - ⚡ **量化回测** — 策略回测与绩效
    """)

    st.markdown("---")
    st.caption("数据源: akshare (免费开源)")
    st.caption("⚠️ 仅供学习演示，不构成投资建议")

# ---- 主页 ----
show_header()
show_disclaimer()

st.markdown("---")

# 快速概览
st.markdown("## 📊 系统概览")

col1, col2, col3 = st.columns(3)
with col1:
    st.info("### 📈 市场看板\n查看A股指数、板块资金流向、涨跌排行")
with col2:
    st.success("### 🔬 集合竞价\n分析9:15-9:25竞价数据，自动评分推荐")
with col3:
    st.warning("### ⚡ 量化回测\n基于历史数据回测竞价策略，评估绩效")

st.markdown("---")

st.markdown("## 🚀 快速开始")
st.markdown("""
1. **查看市场** → 点击左侧 `📈 市场看板` 页面，了解今日大盘概况
2. **扫描竞价** → 进入 `🔬 集合竞价` 页面，点击"开始扫描"获取推荐股票
3. **策略回测** → 在 `⚡ 量化回测` 页面配置参数，运行历史回测
""")

st.markdown("---")
st.markdown("## ⏰ A股交易时间")
st.markdown("""
| 阶段 | 时间 |
|------|------|
| 集合竞价 | 9:15 — 9:25 |
| 连续竞价 (上午) | 9:30 — 11:30 |
| 连续竞价 (下午) | 13:00 — 15:00 |
""")

# 数据状态
st.markdown("---")
st.markdown("## 📦 数据状态")

try:
    from data.database import get_stock_count
    stock_count = get_stock_count()

    c1, c2 = st.columns(2)
    with c1:
        st.metric("股票池", f"{stock_count}" if stock_count else "未加载")
    with c2:
        st.metric("数据库", "SQLite", delta="就绪" if stock_count else "空")
except Exception:
    st.caption("数据库尚未初始化，访问各页面时将自动创建")
