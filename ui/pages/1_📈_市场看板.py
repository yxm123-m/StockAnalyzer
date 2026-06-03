"""
市场看板 — 指数、板块、涨跌排行
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
import pandas as pd
from datetime import datetime
from data.fetcher import fetch_spot_data, fetch_index_daily, fetch_sectors
from data.database import get_stock_count
from ui.components.common import show_disclaimer, format_money, plot_bar, plot_equity_curve

st.set_page_config(page_title="市场看板", page_icon="📈", layout="wide")
show_disclaimer()

st.title("📈 市场数据看板")

# ---- 操作栏 ----
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    st.caption(f"更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
with col2:
    refresh = st.button("🔄 刷新数据", use_container_width=True)
with col3:
    st.caption(f"股票池: {get_stock_count()} 只")

# ---- 指数行情 ----
st.markdown("### 📊 主要指数")

@st.cache_data(ttl=300, show_spinner=False)
def load_index_data():
    indices = []
    index_list = {
        "上证指数": "sh000001", "深证成指": "sz399001",
        "创业板指": "sz399006", "科创50": "sh000688",
    }
    for name, symbol in index_list.items():
        try:
            df = fetch_index_daily(symbol, "20260101")
            if df is not None and not df.empty:
                latest = df.iloc[-1]
                indices.append({
                    'name': name, 'close': latest.get('close', 0),
                    'change_pct': latest.get('change_pct', 0) if 'change_pct' in df.columns
                    else ((latest.get('close', 0) - latest.get('open', 0)) /
                          latest.get('open', 1) * 100),
                    'volume': latest.get('volume', 0),
                })
        except Exception:
            pass
    return indices

indices = load_index_data()

if indices:
    cols = st.columns(len(indices))
    for i, idx in enumerate(indices):
        with cols[i]:
            chg = idx.get('change_pct', 0)
            color = "red" if chg > 0 else "green" if chg < 0 else "gray"
            st.metric(
                idx['name'],
                f"{idx['close']:,.2f}",
                delta=f"{chg:+.2f}%",
                delta_color="normal"
            )
else:
    st.info("无法获取指数数据，请检查网络连接")

# ---- 两栏布局：板块 + 涨跌榜 ----
col_left, col_right = st.columns(2)

with col_left:
    st.markdown("### 🏭 行业板块")
    try:
        sectors = fetch_sectors()
        if sectors is not None and not sectors.empty:
            # 尝试不同列名
            name_col = next((c for c in sectors.columns if '名称' in c or 'name' in c.lower()), sectors.columns[0])
            chg_col = next((c for c in sectors.columns if '涨跌幅' in c or 'change' in c.lower() or 'pct' in c.lower()), None)

            if chg_col:
                sectors_sorted = sectors.sort_values(chg_col, ascending=False)
                top = sectors_sorted.head(10)
                bottom = sectors_sorted.tail(5)
                show = pd.concat([top, bottom])

                fig = plot_bar(
                    show[name_col].tolist(),
                    show[chg_col].tolist(),
                    title="板块涨跌幅 Top10 + Bottom5",
                    xlabel="涨跌幅(%)"
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.dataframe(sectors.head(10), use_container_width=True)
        else:
            st.info("板块数据暂不可用")
    except Exception as e:
        st.info(f"板块数据获取中... ({e})")

with col_right:
    st.markdown("### 🔥 涨跌排行")

    @st.cache_data(ttl=300, show_spinner=False)
    def load_spot():
        return fetch_spot_data()

    spot = load_spot()
    if spot is not None and not spot.empty:
        tab1, tab2 = st.tabs(["📈 涨幅榜", "📉 跌幅榜"])

        with tab1:
            if 'change_pct' in spot.columns:
                top_gainers = spot.nlargest(15, 'change_pct')
            else:
                top_gainers = spot.head(15)
            disp = top_gainers[['code', 'name', 'price', 'change_pct']].copy() if all(
                c in spot.columns for c in ['code', 'name', 'price', 'change_pct']
            ) else top_gainers.head(15)
            st.dataframe(disp, use_container_width=True, hide_index=True,
                         column_config={'change_pct': st.column_config.NumberColumn('涨跌幅', format='%.2f%%')})

        with tab2:
            if 'change_pct' in spot.columns:
                top_losers = spot.nsmallest(15, 'change_pct')
            else:
                top_losers = spot.tail(15)
            disp = top_losers[['code', 'name', 'price', 'change_pct']].copy() if all(
                c in spot.columns for c in ['code', 'name', 'price', 'change_pct']
            ) else top_losers.tail(15)
            st.dataframe(disp, use_container_width=True, hide_index=True,
                         column_config={'change_pct': st.column_config.NumberColumn('涨跌幅', format='%.2f%%')})
    else:
        st.info("实时行情数据暂不可用")

# ---- 指数趋势图 ----
st.markdown("---")
st.markdown("### 📈 指数走势 (近30日)")

idx_choice = st.selectbox("选择指数", ["上证指数", "深证成指", "创业板指", "科创50"])
symbol_map = {"上证指数": "sh000001", "深证成指": "sz399001", "创业板指": "sz399006", "科创50": "sh000688"}

try:
    idx_df = fetch_index_daily(symbol_map[idx_choice], "20260501")
    if idx_df is not None and not idx_df.empty:
        recent = idx_df.tail(30)
        dates = recent['date'].tolist() if 'date' in recent.columns else recent.index.tolist()
        values = recent['close'].tolist() if 'close' in recent.columns else recent.iloc[:, 1].tolist()
        fig = plot_equity_curve(dates, values, title=f"{idx_choice} 近30日走势")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("暂无趋势数据")
except Exception as e:
    st.info(f"趋势图数据获取中...")
