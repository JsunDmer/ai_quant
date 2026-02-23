"""
Stock MVP - 股民投资助手
基于每日收盘模式的决策辅助工具
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

from config import config
from db import db, FollowedStock
from stock_data import stock_data


st.set_page_config(
    page_title="股民间投资助手",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ========== FinTech Light Theme ==========
custom_css = """
    <style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=Noto+Sans+SC:wght@300;400;500;700&display=swap');
    
    /* Root Variables - Light Theme */
    :root {
        --bg-primary: #f8fafc;
        --bg-secondary: #f1f5f9;
        --bg-tertiary: #e2e8f0;
        --bg-card: #ffffff;
        --bg-card-hover: #fafafa;
        --border-color: #e2e8f0;
        --border-strong: #cbd5e1;
        --text-primary: #1e293b;
        --text-secondary: #64748b;
        --text-muted: #94a3b8;
        --accent-green: #10b981;
        --accent-green-dim: rgba(16, 185, 129, 0.1);
        --accent-red: #ef4444;
        --accent-red-dim: rgba(239, 68, 68, 0.1);
        --accent-blue: #3b82f6;
        --accent-cyan: #0891b2;
        --accent-gold: #f59e0b;
        --accent-purple: #8b5cf6;
        --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);
        --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
    }
    
    /* Global Styles */
    .stApp {
        background: var(--bg-primary);
        font-family: 'Noto Sans SC', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Main Content Padding - Compact */
    .block-container {
        padding-top: 0.5rem !important;
        padding-bottom: 1rem !important;
    }
    
    /* Headers - Compact */
    h1, h2, h3, h4, h5, h6 {
        color: var(--text-primary) !important;
        font-weight: 600;
        margin-bottom: 0.5rem;
    }
    
    h1 { font-size: 1.5rem; }
    h2 { font-size: 1.25rem; }
    h3 { font-size: 1.1rem; }
    
    /* Links */
    a {
        color: var(--accent-blue) !important;
        transition: all 0.2s ease;
    }
    a:hover {
        color: var(--accent-cyan) !important;
    }
    
    /* Sidebar - Compact */
    [data-testid="stSidebar"] {
        background: var(--bg-card) !important;
        border-right: 1px solid var(--border-color) !important;
        padding: 12px !important;
    }
    
    [data-testid="stSidebar"] .stMarkdown, 
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label {
        color: var(--text-secondary) !important;
        font-size: 13px;
    }
    
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: var(--text-primary) !important;
        font-size: 14px;
        margin-bottom: 8px;
    }
    
    /* Sidebar Inputs - Compact */
    [data-testid="stSidebar"] .stTextInput > div > div {
        background: var(--bg-secondary) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 6px;
        font-size: 13px;
    }
    
    [data-testid="stSidebar"] .stTextInput > div > div:focus-within {
        border-color: var(--accent-blue) !important;
        box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15) !important;
    }
    
    /* Tab Bar Styling - Compact */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
        background: var(--bg-secondary);
        padding: 4px;
        border-radius: 8px;
        border: 1px solid var(--border-color);
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 36px;
        padding: 0 16px;
        background: transparent;
        border-radius: 6px;
        color: var(--text-secondary);
        font-weight: 500;
        font-size: 13px;
        transition: all 0.2s ease;
    }
    
    .stTabs [aria-selected="true"] {
        background: var(--accent-blue) !important;
        color: #ffffff !important;
        font-weight: 600;
        box-shadow: var(--shadow-sm);
    }
    
    .stTabs [data-baseweb="tab"]:hover:not([aria-selected="true"]) {
        background: var(--bg-card);
        color: var(--text-primary);
    }
    
    /* Metric Cards - Clean Light Style */
    [data-testid="stMetric"] {
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: 8px;
        padding: 12px 16px;
        transition: all 0.2s ease;
        box-shadow: var(--shadow-sm);
    }
    
    [data-testid="stMetric"]:hover {
        background: var(--bg-card-hover);
        border-color: var(--border-strong);
        box-shadow: var(--shadow-md);
    }
    
    [data-testid="stMetricLabel"] {
        color: var(--text-secondary) !important;
        font-size: 11px !important;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.3px;
    }
    
    [data-testid="stMetricValue"] {
        color: var(--text-primary) !important;
        font-family: 'JetBrains Mono', monospace;
        font-weight: 600;
        font-size: 18px !important;
    }
    
    [data-testid="stMetricDelta"] {
        font-family: 'JetBrains Mono', monospace;
        font-weight: 600;
        font-size: 12px;
    }
    
    /* Positive delta (green) */
    [data-testid="stMetricDelta"] svg[dir="up"] {
        color: var(--accent-green) !important;
    }
    
    /* Negative delta (red) */
    [data-testid="stMetricDelta"] svg[dir="down"] {
        color: var(--accent-red) !important;
    }
    
    /* Buttons - Compact */
    .stButton > button {
        font-family: 'Noto Sans SC', sans-serif;
        font-weight: 500;
        border-radius: 6px;
        padding: 8px 16px;
        transition: all 0.2s ease;
        border: none;
        font-size: 13px;
    }
    
    /* Primary Button */
    .stButton > button[kind="primary"] {
        background: var(--accent-blue) !important;
        color: white !important;
        box-shadow: var(--shadow-sm);
    }
    
    .stButton > button[kind="primary"]:hover {
        background: #2563eb !important;
        box-shadow: var(--shadow-md);
    }
    
    /* Secondary Buttons */
    .stButton > button[kind="secondary"] {
        background: var(--bg-card) !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--border-color) !important;
    }
    
    .stButton > button[kind="secondary"]:hover {
        background: var(--bg-secondary) !important;
        border-color: var(--accent-blue) !important;
    }
    
    /* Dividers - Subtle */
    hr {
        border-color: var(--border-color) !important;
        margin: 12px 0;
    }
    
    /* Info/Warning/Success/Error Messages */
    .stAlert {
        border-radius: 8px;
        border: 1px solid;
        padding: 12px 16px;
        font-size: 13px;
    }
    
    /* Info Alert */
    [data-testid="stInfo"] {
        background: rgba(59, 130, 246, 0.08) !important;
        border-color: rgba(59, 130, 246, 0.2) !important;
        color: var(--accent-blue) !important;
    }
    
    /* Success Alert */
    [data-testid="stSuccess"] {
        background: var(--accent-green-dim) !important;
        border-color: rgba(16, 185, 129, 0.2) !important;
        color: #047857 !important;
    }
    
    /* Warning Alert */
    [data-testid="stWarning"] {
        background: rgba(245, 158, 11, 0.08) !important;
        border-color: rgba(245, 158, 11, 0.2) !important;
        color: #b45309 !important;
    }
    
    /* Error Alert */
    [data-testid="stError"] {
        background: var(--accent-red-dim) !important;
        border-color: rgba(239, 68, 68, 0.2) !important;
        color: #b91c1c !important;
    }
    
    /* Select Boxes */
    .stSelectbox > div > div {
        background: var(--bg-card) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 6px;
        font-size: 13px;
    }
    
    .stSelectbox > div > div:focus-within {
        border-color: var(--accent-blue) !important;
        box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15) !important;
    }
    
    /* Cards/Containers - Light with Shadow */
    .stContainer {
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: 8px;
        padding: 16px;
        box-shadow: var(--shadow-sm);
    }
    
    /* Expanders */
    .streamlit-expanderHeader {
        background: var(--bg-card) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 8px !important;
        color: var(--text-primary) !important;
        font-size: 13px;
        padding: 10px 14px !important;
    }
    
    .streamlit-expanderHeader:hover {
        background: var(--bg-secondary) !important;
    }
    
    /* Code Blocks */
    code {
        font-family: 'JetBrains Mono', monospace;
        background: var(--bg-secondary) !important;
        color: var(--accent-gold) !important;
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 12px;
    }
    
    pre {
        background: var(--bg-secondary) !important;
        border: 1px solid var(--border-color);
        border-radius: 6px;
    }
    
    /* Spinner */
    [data-testid="stSpinner"] {
        color: var(--accent-blue);
    }
    
    /* Scrollbar */
    ::-webkit-scrollbar {
        width: 6px;
        height: 6px;
    }
    
    ::-webkit-scrollbar-track {
        background: var(--bg-secondary);
    }
    
    ::-webkit-scrollbar-thumb {
        background: var(--border-strong);
        border-radius: 3px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: var(--text-muted);
    }
    
    /* Caption */
    [data-testid="stCaption"] {
        color: var(--text-muted) !important;
        font-size: 11px;
    }
    
    /* DataFrame/Table Styling */
    [data-testid="stDataFrame"] {
        border: 1px solid var(--border-color);
        border-radius: 8px;
        overflow: hidden;
    }
    
    /* Hide default Streamlit elements */
    footer { visibility: hidden; }
    .stDeployButton { display: none !important; }
    [data-testid="stToolbar"] { display: none !important; }
    [data-testid="stDecoration"] { display: none !important; }
    [data-testid="stHeader"] { display: none !important; }
    header[data-testid="stHeader"] { display: none !important; }
    #MainMenu { display: none !important; }
    
    /* Compact header in main area */
    .app-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 8px 0;
        margin-bottom: 8px;
    }
    
    .app-header h1 {
        font-size: 18px;
        font-weight: 600;
        color: var(--text-primary) !important;
    }
    
    /* Sidebar Header */
    .sidebar-header {
        font-size: 14px;
        font-weight: 600;
        color: var(--text-primary);
        padding: 8px 0;
        margin-bottom: 12px;
        border-bottom: 1px solid var(--border-color);
    }
    
    /* Ensure main content is fully visible */
    .main .block-container {
        max-width: 100% !important;
        padding: 1rem 2rem !important;
    }
    
    /* Fix for tabs being obscured */
    .stTabs {
        margin-bottom: 1rem;
    }
    
    /* Full width for charts */
    .stPlotlyChart {
        width: 100% !important;
    }

    /* ========== Section Header Styles ========== */
    .section-header-up {
        background: linear-gradient(135deg, var(--accent-green-dim), rgba(16, 185, 129, 0.05));
        border: 1px solid rgba(16, 185, 129, 0.25);
        border-radius: 10px;
        padding: 14px 18px;
        margin-bottom: 16px;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .section-header-up h3 {
        color: #047857 !important;
        margin: 0 !important;
        font-size: 1.1rem;
    }

    .section-header-down {
        background: linear-gradient(135deg, var(--accent-red-dim), rgba(239, 68, 68, 0.05));
        border: 1px solid rgba(239, 68, 68, 0.25);
        border-radius: 10px;
        padding: 14px 18px;
        margin-bottom: 16px;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .section-header-down h3 {
        color: #b91c1c !important;
        margin: 0 !important;
        font-size: 1.1rem;
    }

    /* Sector / Stock Card Styles */
    .item-card {
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: 10px;
        padding: 14px 18px;
        margin-bottom: 10px;
        transition: all 0.2s ease;
        box-shadow: var(--shadow-sm);
    }
    .item-card:hover {
        border-color: var(--border-strong);
        box-shadow: var(--shadow-md);
    }
    .item-card-up {
        border-left: 3px solid var(--accent-green);
    }
    .item-card-down {
        border-left: 3px solid var(--accent-red);
    }
    .item-card .card-title {
        font-weight: 600;
        font-size: 15px;
        color: var(--text-primary);
        margin-bottom: 6px;
    }
    .item-card .card-meta {
        font-size: 12px;
        color: var(--text-secondary);
        margin-bottom: 4px;
    }
    .item-card .card-score {
        font-family: 'JetBrains Mono', monospace;
        font-weight: 600;
        font-size: 14px;
    }
    .score-up { color: var(--accent-green); }
    .score-down { color: var(--accent-red); }
    .card-reason {
        font-size: 12px;
        color: var(--text-secondary);
        line-height: 1.5;
        margin-top: 6px;
    }
    .card-stocks {
        margin-top: 8px;
        padding-top: 8px;
        border-top: 1px dashed var(--border-color);
    }
    .card-stocks .stock-tag {
        display: inline-block;
        background: var(--bg-secondary);
        border: 1px solid var(--border-color);
        border-radius: 4px;
        padding: 2px 8px;
        font-size: 12px;
        margin: 2px 4px 2px 0;
        color: var(--text-primary);
    }

    /* Portfolio section */
    .portfolio-section {
        margin-top: 24px;
        padding-top: 16px;
        border-top: 2px solid var(--border-color);
    }
    </style>
"""
st.markdown(custom_css, unsafe_allow_html=True)


def main():
    # ========== 顶部标题栏 ==========
    col_title, col_btn = st.columns([4, 1])
    with col_title:
        st.markdown("### 📈 股民投资助手")
    with col_btn:
        if st.button("🚀 执行分析", type="primary", use_container_width=True):
            with st.spinner("正在分析市场数据..."):
                from pipeline import run_post_close_pipeline
                sources = st.session_state.get('enabled_sources')
                ai_on = st.session_state.get('ai_analysis_enabled', True)
                run_post_close_pipeline(enabled_sources=sources, ai_enabled=ai_on)
            st.success("分析完成！")
            st.rerun()

    # ========== 设置面板（可展开/收起） ==========
    with st.expander("⚙️ 设置", expanded=False):
        # --- 第一行: API / 定时 / AI开关 ---
        col_s1, col_s2, col_s3 = st.columns(3)

        with col_s1:
            api_key = st.text_input("LLM API Key", value=config.LLM_API_KEY, type="password")

        with col_s2:
            schedule_enabled = st.toggle("启用自动执行", value=False, help="每天自动执行收盘分析")
            schedule_time = st.time_input("执行时间", value=None, help="每日自动执行的时间(16:00为收盘后)")

        with col_s3:
            # 定时开启时，AI分析自动绑定并锁定
            if schedule_enabled:
                ai_analysis_enabled = True
                st.toggle("启用AI分析", value=True, disabled=True,
                          help="自动执行模式下 AI 分析默认开启", key="ai_toggle")
                st.caption("🔗 自动执行已绑定AI分析")
            else:
                ai_analysis_enabled = st.toggle("启用AI分析", value=True,
                                                help="执行分析时自动调用AI生成关键词和洞察", key="ai_toggle")
            st.session_state['ai_analysis_enabled'] = ai_analysis_enabled
            latest_snapshot = db.get_latest_market_snapshot()
            if latest_snapshot:
                st.caption(f"📅 上次数据: {latest_snapshot.trade_date}")

        # --- 第二行: 新闻源开关 ---
        st.markdown("**📰 新闻源**")
        from news_collector import ALL_SOURCE_NAMES
        # 初始化 session_state
        if 'enabled_sources' not in st.session_state:
            st.session_state['enabled_sources'] = list(ALL_SOURCE_NAMES)

        src_cols = st.columns(5)
        for i, name in enumerate(ALL_SOURCE_NAMES):
            with src_cols[i % 5]:
                checked = st.checkbox(name, value=(name in st.session_state['enabled_sources']), key=f"src_{name}")
                if checked and name not in st.session_state['enabled_sources']:
                    st.session_state['enabled_sources'].append(name)
                elif not checked and name in st.session_state['enabled_sources']:
                    st.session_state['enabled_sources'].remove(name)

        # 检查是否需要自动执行
        if schedule_enabled and schedule_time:
            now = datetime.now()
            if now.time() >= schedule_time:
                if latest_snapshot is None or latest_snapshot.trade_date != now.strftime('%Y-%m-%d'):
                    st.info("⏰ 已到达定时时间，请点击上方按钮执行分析")

    # ========== 三大模块 Tab ==========
    tab1, tab2, tab3 = st.tabs(["📊 市场分析", "🎯 板块分析", "💰 个股分析"])

    with tab1:
        render_market_overview()

    with tab2:
        render_sector_analysis()

    with tab3:
        render_quant_signals()


def render_market_overview():
    import json

    st.header("📊 市场分析")

    # 查询最新市场快照
    snapshot = db.get_latest_market_snapshot()

    if not snapshot:
        st.info("暂无市场数据，请先点击顶部「执行分析」按钮生成数据")
        return
    
    # 解析 JSON 数据
    try:
        indices = json.loads(snapshot.indices_json) if snapshot.indices_json else {}
    except:
        indices = {}
    
    try:
        market_breadth = json.loads(snapshot.market_breadth_json) if snapshot.market_breadth_json else {}
    except:
        market_breadth = {}
    
    try:
        turnover = json.loads(snapshot.turnover_json) if snapshot.turnover_json else {}
    except:
        turnover = {}
    
    try:
        north_flow = json.loads(snapshot.north_flow_json) if snapshot.north_flow_json else {}
    except:
        north_flow = {}
    
    try:
        news = json.loads(snapshot.news_json) if snapshot.news_json else []
    except:
        news = []
    
    # 词云数据源
    all_news = news
    
    # 显示日期和状态
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.markdown(f"**📅 交易日期:** {snapshot.trade_date}")
    with col2:
        if snapshot.status == "degraded":
            st.warning("⚠️ 降级模式")
    with col3:
        st.markdown(f"*数据更新: {snapshot.created_at}*")
    
    st.markdown("---")
    
    # ========== 上下布局 ==========
    # 词云在上方（更大）
    _render_wordcloud_section(all_news, snapshot.trade_date)
    
    st.markdown("---")
    
    # 市场指数在下方
    _render_indices_section(indices, market_breadth, turnover, north_flow)
    



def _render_wordcloud_section(all_news, trade_date=None):
    st.subheader("📰 新闻热点")
    import json

    ai_news_list = None

    # 1. 优先从 ai_news 表获取AI结构化新闻
    if trade_date:
        ai_news_list = db.get_ai_news(trade_date)

    # 2. 有AI新闻 → 用卡片网格展示
    if ai_news_list:
        st.caption("🤖 数据来源: AI结构化分析")
        _render_news_cards(ai_news_list)
    elif all_news:
        st.caption("📝 数据来源: 原始新闻")
        titles = [n.get("title", "") for n in all_news if isinstance(n, dict) and n.get("title")]
        if titles:
            _render_raw_news_cards(titles)


def _render_news_cards(ai_news_list):
    """用 HTML 卡片网格展示AI新闻：左边框=情绪颜色，信息丰富"""
    import json

    sentiment_cfg = {
        "positive": ("#10b981", "🟢", "利好"),
        "negative": ("#ef4444", "🔴", "利空"),
        "neutral":  ("#94a3b8", "⚪", "中性"),
    }

    cards_html = []
    for n in ai_news_list:
        sentiment = n.sentiment or "neutral"
        color, emoji, label = sentiment_cfg.get(sentiment, ("#94a3b8", "⚪", "中性"))
        importance = max(n.importance or 5, 1)
        title = n.title or ""
        summary = n.summary or ""
        cat = n.category or ""
        url = n.source_url or ""

        # 关联板块
        sector_tags = ""
        try:
            sectors = json.loads(n.related_sectors_json) if n.related_sectors_json else []
            if sectors:
                sector_tags = "".join(
                    f'<span class="nc-sector">{s}</span>' for s in sectors[:3]
                )
        except Exception:
            pass

        # 重要性星级
        stars = "★" * min(importance // 2, 5) + "☆" * max(0, 5 - importance // 2)

        # 标题：有链接则可点击
        if url:
            title_html = f'<a href="{url}" target="_blank" class="nc-link">{title}</a>'
        else:
            title_html = title

        card = f'''<div class="nc-card" style="border-left:4px solid {color};">
  <div class="nc-header">
    <span class="nc-emoji">{emoji}</span>
    <span class="nc-label" style="color:{color};">{label}</span>
    <span class="nc-stars" style="color:{color};">{stars}</span>
  </div>
  <div class="nc-title">{title_html}</div>
  <div class="nc-summary">{summary}</div>
  <div class="nc-footer">
    <span class="nc-cat">{cat}</span>
    {sector_tags}
  </div>
</div>'''
        cards_html.append(card)

    n_cols = 3 if len(ai_news_list) > 4 else 2
    grid_css = f"""
<style>
.nc-grid {{
  display: grid;
  grid-template-columns: repeat({n_cols}, 1fr);
  gap: 10px;
  margin-bottom: 8px;
}}
.nc-card {{
  background: #f8fafc;
  border-radius: 8px;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  transition: box-shadow .15s;
}}
.nc-card:hover {{ box-shadow: 0 2px 8px rgba(0,0,0,.08); }}
.nc-header {{
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
}}
.nc-emoji {{ font-size: 14px; }}
.nc-label {{ font-weight: 600; }}
.nc-stars {{ margin-left: auto; font-size: 11px; letter-spacing: 1px; }}
.nc-title {{
  font-size: 14px;
  font-weight: 600;
  line-height: 1.5;
  color: #1e293b;
}}
.nc-link {{ color: #1e293b; text-decoration: none; }}
.nc-link:hover {{ color: #3b82f6; text-decoration: underline; }}
.nc-summary {{
  font-size: 12px;
  color: #475569;
  line-height: 1.6;
}}
.nc-footer {{
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  margin-top: 2px;
}}
.nc-cat {{
  background: #e2e8f0;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  color: #475569;
  font-weight: 500;
}}
.nc-sector {{
  background: #dbeafe;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  color: #2563eb;
}}
</style>
"""
    html = grid_css + '<div class="nc-grid">' + "\n".join(cards_html) + "</div>"
    st.markdown(html, unsafe_allow_html=True)
    st.caption("🟢 利好 &nbsp;&nbsp; 🔴 利空 &nbsp;&nbsp; ⚪ 中性 &nbsp;&nbsp; | &nbsp;&nbsp; ★ = 重要程度")


def _render_raw_news_cards(titles):
    """原始新闻标题的简易卡片网格"""
    palette = ["#3b82f6", "#6366f1", "#8b5cf6", "#0ea5e9", "#14b8a6",
               "#f59e0b", "#ef4444", "#ec4899", "#10b981", "#64748b"]

    cards_html = []
    for i, title in enumerate(titles[:15]):
        color = palette[i % len(palette)]
        card = f'''<div style="background:{color};color:white;border-radius:6px;
padding:8px 12px;font-size:13px;font-weight:500;line-height:1.4;">{title}</div>'''
        cards_html.append(card)

    n_cols = 3 if len(titles) > 4 else 2
    html = f"""
<div style="display:grid;grid-template-columns:repeat({n_cols},1fr);gap:8px;margin-bottom:8px;">
{"".join(cards_html)}
</div>"""
    st.markdown(html, unsafe_allow_html=True)


def _render_indices_section(indices, market_breadth, turnover, north_flow):
    st.subheader("📈 市场指数")
    index_map = {
        "上证指数": "shanghai",
        "深证成指": "shenzhen",
        "创业板指": "chinext",
        "科创50": "sci_tech",
        "沪深300": "hs300",
        "中证500": "cci500",
        "中证1000": "cci1000"
    }
    cols = st.columns(7)
    for idx, (name, key) in enumerate(index_map.items()):
        with cols[idx]:
            if key in indices:
                data = indices[key]
                price = data.get("price", "N/A")
                change = data.get("change_pct", 0)
                change_str = f"+{change:.2f}%" if change >= 0 else f"{change:.2f}%"
                st.metric(label=name, value=f"{price:.2f}" if isinstance(price, (int, float)) else str(price), delta=change_str)
            else:
                st.metric(label=name, value="暂无")
    
    # 市场广度摘要
    if market_breadth:
        st.markdown("**市场广度**")
        up = market_breadth.get("上涨", market_breadth.get("up", 0))
        down = market_breadth.get("下跌", market_breadth.get("down", 0))
        total = up + down if isinstance(up, int) and isinstance(down, int) else 0
        if total > 0:
            ratio = up / total * 100
            st.metric("涨跌比", f"{ratio:.1f}%", f"上涨 {up} / 下跌 {down}")
    
    # 北向资金
    if north_flow:
        net = north_flow.get("net", north_flow.get("净买入", 0))
        if isinstance(net, (int, float)) and net != 0:
            net_str = f"+{net/100000000:.2f}亿" if net >= 0 else f"{net/100000000:.2f}亿"
            st.metric("北向资金", net_str)


def _render_ai_market_analysis(news, indices):
    st.markdown("---")
    st.subheader("🤖 AI 市场分析")
    
    if st.button("生成 AI 分析", key="gen_ai_analysis"):
        with st.spinner("AI 分析中..."):
            try:
                from ai_analysis import ai_analysis
                from news_crawler import get_international_news
                
                intl_news = get_international_news(5)
                us_indices = {}
                
                result = ai_analysis.analyze_market(news + intl_news, indices, us_indices)
                
                market_view = result.get("market_view", "未知")
                key_insight = result.get("key_insight", "暂无分析")
                hot_keywords = result.get("hot_keywords", [])
                
                view_color = {"乐观": "🟢", "中性偏乐观": "🔵", "中性": "⚪", "中性偏谨慎": "🟡", "谨慎": "🔴"}.get(market_view, "⚪")
                
                st.markdown(f"**市场观点:** {view_color} {market_view}")
                st.markdown(f"**核心洞察:** {key_insight}")
                if hot_keywords:
                    st.markdown(f"**热点关键词:** {', '.join(hot_keywords[:5])}")
                    
            except Exception as e:
                st.error(f"AI 分析失败: {e}")


def render_sector_analysis():
    import json

    st.header("🎯 板块分析")

    # ========== 查询数据 ==========
    # 1. AI板块分析数据（上涨/下跌方向）
    ai_sector_analysis = db.get_latest_ai_sector_analysis()

    # 2. 板块推荐数据（评分）
    sector_recs = db.get_latest_sector_recommendations()

    # 3. 股票信号（用于显示板块下的推荐个股）
    stock_signals = db.get_latest_stock_signals(limit=100)

    if not ai_sector_analysis and not sector_recs:
        st.info("暂无板块分析数据，请先执行「收盘分析」生成数据")
        return

    # 构建 sector -> 推荐股票 的映射
    sector_stocks = {}
    for signal in stock_signals:
        if signal.signal in ["buy", "strong_buy"] and signal.confidence >= 0.6:
            if signal.sector_name not in sector_stocks:
                sector_stocks[signal.sector_name] = []
            sector_stocks[signal.sector_name].append({
                "stock_code": signal.stock_code,
                "stock_name": signal.stock_name,
                "confidence": signal.confidence
            })

    # 构建板块评分映射
    sector_score_map = {}
    sector_reasons_map = {}
    if sector_recs:
        for rec in sector_recs:
            sector_score_map[rec.sector_name] = rec.score
            reasons = []
            try:
                if rec.reasons_json:
                    reasons = json.loads(rec.reasons_json)
                    if isinstance(reasons, dict):
                        reasons = reasons.get("reasons", reasons.get("推荐理由", []))
            except:
                reasons = []
            sector_reasons_map[rec.sector_name] = reasons

    # 分类上涨/下跌板块
    up_sectors = []
    down_sectors = []

    if ai_sector_analysis:
        for sector in ai_sector_analysis:
            item = {
                "name": sector.sector_name,
                "score_up": getattr(sector, 'score_up', 0),
                "score_down": getattr(sector, 'score_down', 0),
                "confidence": getattr(sector, 'confidence', 0),
                "direction": sector.direction,
                "rec_score": sector_score_map.get(sector.sector_name, 0),
                "reasons": [],
                "stocks": sector_stocks.get(sector.sector_name, [])
            }
            try:
                if sector.reasons_json:
                    r = json.loads(sector.reasons_json)
                    item["reasons"] = r if isinstance(r, list) else []
            except:
                pass
            # 补充板块推荐理由
            if not item["reasons"] and sector.sector_name in sector_reasons_map:
                item["reasons"] = sector_reasons_map[sector.sector_name]

            if sector.direction == "up":
                up_sectors.append(item)
            elif sector.direction == "down":
                down_sectors.append(item)

    # 如果没有AI分析数据，从板块推荐中按评分分类
    if not ai_sector_analysis and sector_recs:
        for rec in sector_recs:
            reasons = sector_reasons_map.get(rec.sector_name, [])
            item = {
                "name": rec.sector_name,
                "score_up": rec.score if rec.score >= 60 else 0,
                "score_down": 100 - rec.score if rec.score < 60 else 0,
                "confidence": rec.score / 100,
                "direction": "up" if rec.score >= 60 else "down",
                "rec_score": rec.score,
                "reasons": reasons,
                "stocks": sector_stocks.get(rec.sector_name, [])
            }
            if rec.score >= 60:
                up_sectors.append(item)
            else:
                down_sectors.append(item)

    # 排序
    up_sectors.sort(key=lambda x: (x["score_up"], x["confidence"]), reverse=True)
    down_sectors.sort(key=lambda x: (x["score_down"], x["confidence"]), reverse=True)

    # 显示数据日期
    if ai_sector_analysis:
        st.caption(f"📅 数据日期: {ai_sector_analysis[0].trade_date}")

    st.markdown("---")

    # ========== 左右分栏布局 ==========
    col_left, col_right = st.columns(2)

    # ===== 左侧: 预估上涨板块 =====
    with col_left:
        st.markdown('<div class="section-header-up"><h3>📈 预估上涨板块</h3></div>', unsafe_allow_html=True)

        if up_sectors:
            for sector in up_sectors[:8]:
                _render_sector_card(sector, direction="up")
        else:
            st.info("暂无预估上涨板块")

    # ===== 右侧: 预估下跌板块 =====
    with col_right:
        st.markdown('<div class="section-header-down"><h3>📉 预估下跌板块</h3></div>', unsafe_allow_html=True)

        if down_sectors:
            for sector in down_sectors[:8]:
                _render_sector_card(sector, direction="down")
        else:
            st.info("暂无预估下跌板块")


def _render_sector_card(sector, direction="up"):
    """渲染单个板块卡片"""
    card_class = "item-card-up" if direction == "up" else "item-card-down"
    score_class = "score-up" if direction == "up" else "score-down"

    prob_label = "上涨概率" if direction == "up" else "下跌概率"
    prob_value = sector["score_up"] if direction == "up" else sector["score_down"]

    with st.container():
        col_info, col_score = st.columns([3, 1])
        with col_info:
            st.markdown(f"**{sector['name']}**")
            # 概率和置信度
            col_a, col_b = st.columns(2)
            with col_a:
                st.metric(prob_label, f"{prob_value}%")
            with col_b:
                st.metric("置信度", f"{sector['confidence']}")
        with col_score:
            if sector["rec_score"] > 0:
                st.metric("评分", f"{sector['rec_score']:.0f}")

        # 推荐理由
        if sector["reasons"]:
            for reason in sector["reasons"][:2]:
                st.caption(f"• {reason}")

        # 推荐个股
        if sector["stocks"]:
            stock_tags = " ".join([f"`{s['stock_name']}`" for s in sector["stocks"][:4]])
            st.markdown(f"**个股:** {stock_tags}")

        st.markdown("---")


def render_quant_signals():
    import json

    st.header("💰 个股分析")

    # ========== 查询数据 ==========
    all_signals = db.get_latest_stock_signals(limit=200)

    # ========== 分类到买入和卖出 ==========
    buy_signals = []
    sell_signals = []

    if all_signals:
        for signal in all_signals:
            if signal.signal in ["strong_buy", "buy"]:
                buy_signals.append(signal)
            elif signal.signal in ["strong_sell", "sell"]:
                sell_signals.append(signal)

    # ========== 显示数据日期 ==========
    if all_signals:
        st.caption(f"📅 数据日期: {all_signals[0].trade_date}")

    st.markdown("---")

    # ========== 左右分栏布局 ==========
    col_left, col_right = st.columns(2)

    # ===== 左侧: 预估上涨个股 =====
    with col_left:
        st.markdown('<div class="section-header-up"><h3>📈 预估上涨个股</h3></div>', unsafe_allow_html=True)

        if buy_signals:
            # 按置信度排序
            buy_signals.sort(key=lambda x: x.confidence, reverse=True)

            for signal in buy_signals[:10]:
                # 解析因子
                factors = []
                try:
                    if signal.factors_json:
                        factors = json.loads(signal.factors_json)
                        if isinstance(factors, dict):
                            factors = factors.get("factors", factors.get("因子", []))
                except:
                    factors = []

                signal_display = "强力买入" if signal.signal == "strong_buy" else "买入"
                confidence_pct = signal.confidence * 100

                with st.container():
                    col_name, col_conf = st.columns([3, 1])
                    with col_name:
                        st.markdown(f"**{signal.stock_name}** ({signal.stock_code})")
                        st.caption(f"板块: {signal.sector_name} | 信号: {signal_display}")
                    with col_conf:
                        st.metric("置信度", f"{confidence_pct:.0f}%")

                    # 显示原因
                    if factors:
                        if isinstance(factors, list) and factors:
                            first_factor = factors[0]
                            if isinstance(first_factor, dict):
                                st.caption(f"• {first_factor.get('name', first_factor.get('因子', ''))}")
                            else:
                                st.caption(f"• {first_factor}")

                    st.markdown("---")
        else:
            st.info("暂无预估上涨个股")

    # ===== 右侧: 预估下跌个股 =====
    with col_right:
        st.markdown('<div class="section-header-down"><h3>📉 预估下跌个股</h3></div>', unsafe_allow_html=True)

        if sell_signals:
            # 按置信度排序
            sell_signals.sort(key=lambda x: x.confidence, reverse=True)

            for signal in sell_signals[:10]:
                factors = []
                try:
                    if signal.factors_json:
                        factors = json.loads(signal.factors_json)
                        if isinstance(factors, dict):
                            factors = factors.get("factors", factors.get("因子", []))
                except:
                    factors = []

                signal_display = "强力卖出" if signal.signal == "strong_sell" else "卖出"
                confidence_pct = signal.confidence * 100

                with st.container():
                    col_name, col_conf = st.columns([3, 1])
                    with col_name:
                        st.markdown(f"**{signal.stock_name}** ({signal.stock_code})")
                        st.caption(f"板块: {signal.sector_name} | 信号: {signal_display}")
                    with col_conf:
                        st.metric("置信度", f"{confidence_pct:.0f}%")

                    if factors:
                        if isinstance(factors, list) and factors:
                            first_factor = factors[0]
                            if isinstance(first_factor, dict):
                                st.caption(f"• {first_factor.get('name', first_factor.get('因子', ''))}")
                            else:
                                st.caption(f"• {first_factor}")

                    st.markdown("---")
        else:
            st.info("暂无预估下跌个股")

    # ========== 我的持仓 ==========
    st.markdown("---")
    st.subheader("📊 我的持仓")

    try:
        user_positions = db.get_all_stocks()
    except:
        user_positions = []

    # ===== 添加个股表单 =====
    with st.expander("➕ 添加自持个股", expanded=False):
        with st.form("add_stock_form", clear_on_submit=True):
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                new_code = st.text_input("股票代码", placeholder="例: 600519")
                new_name = st.text_input("股票名称", placeholder="例: 贵州茅台")
            with col_b:
                new_cost = st.number_input("成本价", min_value=0.0, step=0.01, format="%.2f")
                new_volume = st.number_input("持仓数量(股)", min_value=0, step=100)
            with col_c:
                new_alarm_pct = st.number_input("报警涨跌幅(%)", min_value=0.0, value=3.0, step=0.5, format="%.1f")
                new_alarm_price = st.number_input("报警价格", min_value=0.0, step=0.01, format="%.2f")

            submitted = st.form_submit_button("添加", type="primary", use_container_width=True)
            if submitted:
                if new_code and new_name:
                    new_stock = FollowedStock(
                        stock_code=new_code.strip(),
                        stock_name=new_name.strip(),
                        cost_price=new_cost,
                        volume=new_volume,
                        alarm_percent=new_alarm_pct,
                        alarm_price=new_alarm_price,
                    )
                    db.add_stock(new_stock)
                    st.success(f"已添加 {new_name}({new_code})")
                    st.rerun()
                else:
                    st.warning("请填写股票代码和名称")

    # ===== 持仓列表 =====
    if user_positions:
        for pos in user_positions:
            col_info, col_data, col_action = st.columns([3, 3, 1])
            with col_info:
                st.markdown(f"**{pos.stock_name}** ({pos.stock_code})")
            with col_data:
                st.caption(f"成本: {pos.cost_price:.2f} | 数量: {pos.volume} | 报警: ±{pos.alarm_percent}%")
            with col_action:
                if st.button("删除", key=f"del_{pos.stock_code}", type="secondary"):
                    db.remove_stock(pos.stock_code)
                    st.rerun()
    else:
        st.info("暂无持仓，点击上方「添加自持个股」添加")


if __name__ == "__main__":
    main()
