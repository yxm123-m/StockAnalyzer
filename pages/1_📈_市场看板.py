"""
市场看板 — 指数、板块、涨跌排行 (实时数据)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import pandas as pd
from datetime import datetime
from data.fetcher import fetch_spot_data, fetch_index_daily, fetch_sectors
from data.database import get_stock_count
from common import show_disclaimer, plot_bar, plot_equity_curve

st.set_page_config(page_title="市场看板", page_icon="📈", layout="wide")
show_disclaimer()

st.title("📈 市场数据看板")

col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    st.caption(f"更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
with col2:
    refresh = st.button("🔄 刷新数据", use_container_width=True)
    if refresh:
        st.cache_data.clear()
        st.rerun()
with col3:
    st.caption(f"股票池: {get_stock_count()} 只")

st.markdown("### 📊 主要指数")

@st.cache_data(ttl=60, show_spinner=False)
def load_index_data():
    indices = []
    index_list = {"上证指数":"sh000001","深证成指":"sz399001","创业板指":"sz399006","科创50":"sh000688"}
    for name, symbol in index_list.items():
        try:
            df = fetch_index_daily(symbol, "20260101")
            if df is not None and not df.empty:
                latest = df.iloc[-1]
                chg = latest.get('change_pct', 0) if 'change_pct' in df.columns \
                    else ((latest.get('close',0)-latest.get('open',0))/latest.get('open',1)*100)
                indices.append({'name':name,'close':latest.get('close',0),'change_pct':chg})
        except Exception:
            pass
    return indices

indices = load_index_data()
if indices:
    cols = st.columns(len(indices))
    for i, idx in enumerate(indices):
        with cols[i]:
            st.metric(idx['name'], f"{idx['close']:,.2f}", delta=f"{idx['change_pct']:+.2f}%")
else:
    st.info("无法获取指数数据")

col_left, col_right = st.columns(2)
with col_left:
    st.markdown("### 🏭 行业板块")
    try:
        sectors = fetch_sectors()
        if sectors is not None and not sectors.empty:
            name_col = next((c for c in sectors.columns if '名称' in c or 'name' in c.lower()), sectors.columns[0])
            chg_col = next((c for c in sectors.columns if '涨跌幅' in c or 'change' in c.lower() or 'pct' in c.lower()), None)
            if chg_col:
                show = pd.concat([sectors.sort_values(chg_col, ascending=False).head(10),
                                  sectors.sort_values(chg_col).head(5)])
                fig = plot_bar(show[name_col].tolist(), show[chg_col].tolist(),
                              title="板块涨跌幅 Top10 + Bottom5")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.dataframe(sectors.head(10), use_container_width=True)
        else:
            st.info("板块数据暂不可用")
    except Exception:
        st.info("板块数据获取中...")

with col_right:
    st.markdown("### 🔥 涨跌排行")

    def load_spot():
        """实时行情 — 不使用缓存"""
        return fetch_spot_data()

    spot = load_spot()
    if spot is not None and not spot.empty:
        tab1, tab2 = st.tabs(["📈 涨幅榜", "📉 跌幅榜"])
        with tab1:
            top = spot.nlargest(15, 'change_pct') if 'change_pct' in spot.columns else spot.head(15)
            st.dataframe(top[['code','name','price','change_pct']] if all(c in spot.columns for c in ['code','name','price','change_pct']) else top.head(15),
                        use_container_width=True, hide_index=True)
        with tab2:
            bot = spot.nsmallest(15, 'change_pct') if 'change_pct' in spot.columns else spot.tail(15)
            st.dataframe(bot[['code','name','price','change_pct']] if all(c in spot.columns for c in ['code','name','price','change_pct']) else bot.tail(15),
                        use_container_width=True, hide_index=True)
    else:
        st.info("实时行情数据暂不可用")

st.markdown("---")
st.markdown("### 📈 指数走势 (近30日)")
idx_choice = st.selectbox("选择指数", ["上证指数","深证成指","创业板指","科创50"])
symbol_map = {"上证指数":"sh000001","深证成指":"sz399001","创业板指":"sz399006","科创50":"sh000688"}
try:
    idx_df = fetch_index_daily(symbol_map[idx_choice], "20260501")
    if idx_df is not None and not idx_df.empty:
        recent = idx_df.tail(30)
        dates = recent['date'].tolist() if 'date' in recent.columns else recent.index.tolist()
        values = recent['close'].tolist() if 'close' in recent.columns else recent.iloc[:,1].tolist()
        st.plotly_chart(plot_equity_curve(dates, values, f"{idx_choice} 近30日走势"), use_container_width=True)
    else:
        st.info("暂无趋势数据")
except Exception:
    st.info("趋势图数据获取中...")
