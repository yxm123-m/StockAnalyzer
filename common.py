"""
UI 通用组件 — 免责声明、格式化工具、图表工厂
(Streamlit Cloud 部署版 — 放在根目录)
"""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from config import DISCLAIMER_TEXT


def show_disclaimer():
    """显示免责声明横幅"""
    st.warning(DISCLAIMER_TEXT)


def show_header():
    """页面公共头部"""
    st.markdown("""
    <style>
    .main-header { font-size: 2rem; font-weight: bold; margin-bottom: 0; }
    .sub-header { color: #888; font-size: 0.9rem; margin-bottom: 1rem; }
    </style>
    """, unsafe_allow_html=True)


def format_money(v):
    """格式化金额"""
    if v is None:
        return "—"
    if abs(v) >= 1e8:
        return f"{v/1e8:.2f}亿"
    elif abs(v) >= 1e4:
        return f"{v/1e4:.2f}万"
    else:
        return f"{v:,.2f}"


def format_pct(v):
    """格式化百分比"""
    if v is None:
        return "—"
    color = "red" if v > 0 else "green" if v < 0 else "gray"
    return f":{color}[{v:+.2f}%]"


def plot_equity_curve(dates, values, title="权益曲线"):
    """Plotly 权益曲线"""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates, y=values,
        mode='lines', fill='tozeroy',
        line=dict(color='#E94560', width=2),
        name='权益'
    ))
    fig.update_layout(
        title=title,
        xaxis_title="日期",
        yaxis_title="权益 (¥)",
        template="plotly_dark",
        height=350, margin=dict(l=20, r=20, t=40, b=20),
    )
    return fig


def plot_pie(labels, values, title="分布"):
    """Plotly 饼图"""
    fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=0.3)])
    fig.update_layout(
        title=title,
        template="plotly_dark",
        height=300, margin=dict(l=20, r=20, t=40, b=20),
    )
    return fig


def plot_bar(x, y, title="", xlabel="", ylabel=""):
    """Plotly 柱状图"""
    fig = go.Figure(data=[go.Bar(x=x, y=y, marker_color='#E94560')])
    fig.update_layout(
        title=title, xaxis_title=xlabel, yaxis_title=ylabel,
        template="plotly_dark",
        height=300, margin=dict(l=20, r=20, t=40, b=20),
    )
    return fig


def score_color(score):
    """根据分数返回颜色"""
    if score >= 70:
        return "background-color: #2e7d32; color: white;"
    elif score >= 50:
        return "background-color: #1565c0; color: white;"
    elif score >= 35:
        return "background-color: #f9a825; color: black;"
    else:
        return "background-color: #616161; color: white;"
