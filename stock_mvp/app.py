"""
Stock MVP - 股民投资助手
基于每日收盘模式的决策辅助工具
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

from config import config
from db import db, FollowedStock
from data.stock_data import stock_data


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


def _search_stock(keyword: str) -> list:
    """搜索股票（支持名称/代码/拼音，~100ms），返回匹配列表"""
    import requests
    try:
        url = 'https://searchapi.eastmoney.com/api/suggest/get'
        params = {
            'input': keyword, 'type': 14, 'count': 8,
            'token': 'D43BF722C8E33BDC906FB84D85E326E8',
        }
        r = requests.get(url, params=params, timeout=5)
        items = r.json().get('QuotationCodeTable', {}).get('Data', [])
        results = []
        for item in items:
            mkt = item.get('MktNum', '')
            # 只保留沪深A股 (MktNum: 0=深, 1=沪)
            if mkt not in ('0', '1'):
                continue
            code = item['Code']
            results.append({'code': code, 'name': item['Name']})
        return results
    except Exception as e:
        print(f"搜索股票失败: {e}")
    return []


def _lookup_stock(code: str) -> dict:
    """根据股票代码查询行情（~50ms），返回 dict 或 None"""
    import requests
    try:
        market = "1" if code.startswith("6") else "0"
        url = (
            f"https://push2.eastmoney.com/api/qt/stock/get"
            f"?secid={market}.{code}"
            f"&fields=f57,f58,f43,f170"
            f"&ut=fa5fd1943c7b386f172d6893dbbd1"
        )
        r = requests.get(url, timeout=5)
        data = r.json().get("data")
        if data and data.get("f58"):
            return {
                'name': data["f58"],
                'price': data.get("f43", 0) / 100,
                'change': data.get("f170", 0) / 100,
            }
    except Exception as e:
        print(f"查询股票失败: {e}")
    return None


def main():
    # ========== 顶部标题栏 ==========
    col_title, col_btn = st.columns([4, 1])
    with col_title:
        st.markdown("### 📈 股民投资助手")
    with col_btn:
        if st.button("🚀 执行分析", type="primary", width="stretch"):
            with st.spinner("正在分析市场数据..."):
                from pipeline import run_post_close_pipeline, get_trading_date

                sources = st.session_state.get('enabled_sources')
                ai_on = st.session_state.get('ai_analysis_enabled', True)

                # 使用实际交易日期（处理周末自动回退）
                trade_date, _ = get_trading_date()

                # 检查该交易日期是否已有新闻分析（已搜索过）
                has_news = db.has_ai_news_for_date(trade_date)

                # 如果当天已有新闻分析，则只更新实时数据
                refresh_realtime_only = has_news

                if refresh_realtime_only:
                    st.info("✓ 当天已搜索过新闻，现在仅更新实时市场数据...")

                run_post_close_pipeline(enabled_sources=sources, ai_enabled=ai_on, refresh_realtime_only=refresh_realtime_only)
            st.success("分析完成！")
            st.rerun()

    # ========== 设置面板（可展开/收起） ==========
    with st.expander("⚙️ 设置", expanded=False):
        # --- 第一行: API / 定时 / AI开关 ---
        col_s1, col_s2, col_s3 = st.columns(3)

        with col_s1:
            api_key = st.text_input("LLM API Key", value=config.LLM_API_KEY, type="password")

        with col_s2:
            auto_refresh = st.toggle("自动刷新", value=False, help="每隔N分钟自动刷新市场数据")
            refresh_min = st.number_input("刷新间隔(分钟)", min_value=1, max_value=60, value=5, step=1)
            schedule_enabled = st.toggle("收盘定时分析", value=False, help="每天到指定时间自动执行完整分析")
            schedule_time = st.time_input("执行时间", value=None, help="每日自动执行的时间(16:00为收盘后)")
            st.session_state['_auto_refresh'] = auto_refresh
            st.session_state['_refresh_min'] = refresh_min
            st.session_state['_schedule_enabled'] = schedule_enabled

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
        from data.news_collector import ALL_SOURCE_NAMES
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
                from pipeline import run_post_close_pipeline, get_trading_date
                trade_date, data_date = get_trading_date(now.strftime('%Y-%m-%d'))
                if trade_date != data_date:
                    st.info("📅 非交易日，自动跳过执行")
                elif latest_snapshot is None or latest_snapshot.trade_date != trade_date:
                    st.info("⏰ 定时任务触发，正在自动执行分析...")
                    with st.spinner("自动执行收盘分析中..."):
                        sources = st.session_state.get('enabled_sources')
                        ai_on = st.session_state.get('ai_analysis_enabled', True)
                        # 检查该交易日期是否已有新闻分析
                        has_news = db.has_ai_news_for_date(trade_date)

                        # 如果当天已有新闻分析，则只更新实时数据
                        refresh_realtime_only = has_news

                        if refresh_realtime_only:
                            st.info("📈 当天已搜索过新闻，仅更新实时数据...")

                        run_post_close_pipeline(enabled_sources=sources, ai_enabled=ai_on, refresh_realtime_only=refresh_realtime_only)
                    st.success("✅ 定时分析完成！")
                    st.rerun()

    # ========== 自动刷新逻辑 ==========
    _auto = st.session_state.get('_auto_refresh')
    _interval = st.session_state.get('_refresh_min', 5)

    if _auto:
        # 每次页面加载时，检查是否需要刷新市场数据
        _last_refresh = st.session_state.get('_last_refresh_ts', 0)
        import time as _time
        if _time.time() - _last_refresh > _interval * 60:
            try:
                from data.market_data import MarketData
                from db import MarketSnapshot
                import json as _json
                _m = MarketData()
                _snap = _m.collect_post_close_snapshot()
                if _snap.get('indices'):
                    db.upsert_market_snapshot(MarketSnapshot(
                        trade_date=_snap['trade_date'],
                        indices_json=_json.dumps(_snap.get('indices', []), ensure_ascii=False),
                        market_breadth_json=_json.dumps(_snap.get('market_breadth', {}), ensure_ascii=False),
                        turnover_json=_json.dumps(_snap.get('turnover', {}), ensure_ascii=False),
                        north_flow_json=_json.dumps(_snap.get('north_flow', {}), ensure_ascii=False),
                        news_json=_json.dumps(_snap.get('news', []), ensure_ascii=False),
                        status=_snap.get('status', 'ok'),
                    ))
                st.session_state['_last_refresh_ts'] = _time.time()
            except Exception as e:
                print(f"自动刷新市场数据失败: {e}")

        # JS 定时刷新页面
        st.markdown(
            f'''<script>
            setTimeout(function(){{ window.location.reload(); }}, {_interval * 60 * 1000});
            </script>''',
            unsafe_allow_html=True,
        )
        st.caption(f"🔄 自动刷新已开启，每 {_interval} 分钟更新")

    # ========== 五大模块 Tab ==========
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 市场分析", "🎯 板块分析", "💰 个股分析",
        "📋 评估报告", "📈 量化策略评估"
    ])

    with tab1:
        render_market_overview()

    with tab2:
        render_sector_analysis()

    with tab3:
        render_quant_signals()

    with tab4:
        render_evaluation_report()

    with tab5:
        render_trade_evaluation()


def render_market_overview():
    import json

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
    st.subheader("📈 市场概览")

    # 市场广度摘要
    if market_breadth:
        col1, col2, col3 = st.columns(3)
        up = market_breadth.get("上涨", market_breadth.get("up", 0))
        down = market_breadth.get("下跌", market_breadth.get("down", 0))
        flat = market_breadth.get("平盘", market_breadth.get("flat", 0))
        total = up + down + flat if isinstance(up, int) and isinstance(down, int) else 0

        with col1:
            st.metric("上涨", f"{up}")
        with col2:
            st.metric("下跌", f"{down}")
        with col3:
            if total > 0:
                ratio = up / total * 100
                st.metric("涨跌比", f"{ratio:.1f}%")
            else:
                st.metric("涨跌比", "N/A")

    # 北向资金
    if north_flow:
        net = north_flow.get("net", north_flow.get("净买入", 0))
        if isinstance(net, (int, float)) and net != 0:
            net_str = f"+{net/100000000:.2f}亿" if net >= 0 else f"{net/100000000:.2f}亿"
            st.metric("北向资金", net_str)


def render_sector_analysis():
    import json

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

    # ========== 查询数据 ==========
    all_signals = db.get_latest_stock_signals(limit=200)

    # ========== 分类到买入和卖出 ==========
    buy_signals = []
    sell_signals = []

    # 获取自持股票代码，用于筛选下跌信号
    followed = db.get_all_stocks()
    followed_codes = {s.stock_code for s in followed}

    if all_signals:
        for signal in all_signals:
            if signal.signal in ["strong_buy", "buy"]:
                buy_signals.append(signal)
            elif signal.signal in ["strong_sell", "sell"]:
                # 只保留自持股票的卖出信号
                if signal.stock_code in followed_codes:
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
            # 按更新时间排序（最新的在前），再按置信度排序
            buy_signals.sort(key=lambda x: (x.created_at, x.confidence), reverse=True)

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
                    col_name, col_conf, col_time = st.columns([2, 1, 1])
                    with col_name:
                        st.markdown(f"**{signal.stock_name}** ({signal.stock_code})")
                        st.caption(f"板块: {signal.sector_name} | 信号: {signal_display}")
                    with col_conf:
                        st.metric("置信度", f"{confidence_pct:.0f}%")
                    with col_time:
                        st.metric("更新", signal.created_at.split(" ")[0] if signal.created_at else "-")

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
            # 按更新时间排序（最新的在前），再按置信度排序
            sell_signals.sort(key=lambda x: (x.created_at, x.confidence), reverse=True)

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
                    col_name, col_conf, col_time = st.columns([2, 1, 1])
                    with col_name:
                        st.markdown(f"**{signal.stock_name}** ({signal.stock_code})")
                        st.caption(f"板块: {signal.sector_name} | 信号: {signal_display}")
                    with col_conf:
                        st.metric("置信度", f"{confidence_pct:.0f}%")
                    with col_time:
                        st.metric("更新", signal.created_at.split(" ")[0] if signal.created_at else "-")

                    if factors:
                        if isinstance(factors, list) and factors:
                            first_factor = factors[0]
                            if isinstance(first_factor, dict):
                                st.caption(f"• {first_factor.get('name', first_factor.get('因子', ''))}")
                            else:
                                st.caption(f"• {first_factor}")

                    st.markdown("---")
        else:
            st.info("自持股票中暂无下跌信号" if followed_codes else "请先添加自持个股")

    # ========== 我的持仓 ==========
    st.markdown("---")
    st.subheader("📊 我的持仓")

    try:
        user_positions = db.get_all_stocks()
    except:
        user_positions = []

    # ===== 添加个股 =====
    with st.expander("➕ 添加自持个股", expanded=False):
        # Step 1: 搜索（支持名称/代码/拼音）
        col_search, col_btn = st.columns([3, 1])
        with col_search:
            search_kw = st.text_input("搜索股票", placeholder="输入名称、代码或拼音，如: 茅台 / 600519 / mt", key="search_stock_kw")
        with col_btn:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🔍 搜索", width="stretch"):
                kw = search_kw.strip()
                if kw:
                    with st.spinner("搜索中..."):
                        results = _search_stock(kw)
                    if results:
                        st.session_state['_search_results'] = results
                        st.session_state.pop('_found_stock', None)
                    else:
                        st.session_state.pop('_search_results', None)
                        st.session_state.pop('_found_stock', None)
                        st.warning(f"未找到「{kw}」相关股票")

        # Step 2: 显示搜索结果列表，点击选择
        search_results = st.session_state.get('_search_results')
        if search_results and not st.session_state.get('_found_stock'):
            cols = st.columns(min(len(search_results), 4))
            for i, item in enumerate(search_results[:8]):
                with cols[i % 4]:
                    if st.button(f"{item['name']}\n{item['code']}", key=f"pick_{item['code']}", width="stretch"):
                        with st.spinner("查询行情..."):
                            detail = _lookup_stock(item['code'])
                        if detail:
                            st.session_state['_found_stock'] = {'code': item['code'], **detail}
                        else:
                            st.session_state['_found_stock'] = {'code': item['code'], 'name': item['name'], 'price': 0, 'change': 0}
                        st.rerun()

        # Step 3: 选中后显示行情 + 添加表单
        found = st.session_state.get('_found_stock')
        if found:
            chg = found['change']
            color = "#10b981" if chg >= 0 else "#ef4444"
            st.markdown(
                f"**{found['name']}** ({found['code']}) &nbsp; "
                f"最新价 {found['price']:.2f} &nbsp; "
                f"<span style='color:{color};'>{'↑' if chg >= 0 else '↓'}{abs(chg):.2f}%</span>",
                unsafe_allow_html=True,
            )
            with st.form("add_stock_form", clear_on_submit=True):
                col_b, col_c = st.columns(2)
                with col_b:
                    new_cost = st.number_input("成本价", min_value=0.0, value=found['price'], step=0.01, format="%.2f")
                    new_volume = st.number_input("持仓数量(股)", min_value=0, step=100)
                with col_c:
                    new_alarm_pct = st.number_input("报警涨跌幅(%)", min_value=0.0, value=3.0, step=0.5, format="%.1f")
                    new_alarm_price = st.number_input("报警价格", min_value=0.0, step=0.01, format="%.2f")

                if st.form_submit_button("✅ 确认添加", type="primary", width="stretch"):
                    new_stock = FollowedStock(
                        stock_code=found['code'],
                        stock_name=found['name'],
                        cost_price=new_cost,
                        volume=new_volume,
                        alarm_percent=new_alarm_pct,
                        alarm_price=new_alarm_price,
                    )
                    db.add_stock(new_stock)
                    st.session_state.pop('_found_stock', None)
                    st.session_state.pop('_search_results', None)
                    st.success(f"已添加 {found['name']}({found['code']})")
                    st.rerun()

    # ===== 持仓列表（支持修改） =====
    if user_positions:
        for pos in user_positions:
            edit_key = f"_edit_{pos.stock_code}"
            is_editing = st.session_state.get(edit_key, False)

            if not is_editing:
                # 展示模式
                col_info, col_data, col_edit, col_del = st.columns([3, 4, 1, 1])
                with col_info:
                    st.markdown(f"**{pos.stock_name}** ({pos.stock_code})")
                with col_data:
                    st.caption(f"成本: {pos.cost_price:.2f} | 数量: {pos.volume} | 报警: ±{pos.alarm_percent}%")
                with col_edit:
                    if st.button("修改", key=f"edit_{pos.stock_code}"):
                        st.session_state[edit_key] = True
                        st.rerun()
                with col_del:
                    if st.button("删除", key=f"del_{pos.stock_code}", type="secondary"):
                        db.remove_stock(pos.stock_code)
                        st.rerun()
            else:
                # 编辑模式
                st.markdown(f"✏️ 修改 **{pos.stock_name}** ({pos.stock_code})")
                with st.form(f"edit_form_{pos.stock_code}"):
                    col_b, col_c = st.columns(2)
                    with col_b:
                        edit_cost = st.number_input("成本价", min_value=0.0, value=float(pos.cost_price), step=0.01, format="%.2f", key=f"ec_{pos.stock_code}")
                        edit_volume = st.number_input("持仓数量(股)", min_value=0, value=int(pos.volume), step=100, key=f"ev_{pos.stock_code}")
                    with col_c:
                        edit_alarm_pct = st.number_input("报警涨跌幅(%)", min_value=0.0, value=float(pos.alarm_percent), step=0.5, format="%.1f", key=f"ea_{pos.stock_code}")
                        edit_alarm_price = st.number_input("报警价格", min_value=0.0, value=float(pos.alarm_price), step=0.01, format="%.2f", key=f"ep_{pos.stock_code}")

                    col_save, col_cancel = st.columns(2)
                    with col_save:
                        if st.form_submit_button("💾 保存", type="primary", width="stretch"):
                            updated = FollowedStock(
                                stock_code=pos.stock_code,
                                stock_name=pos.stock_name,
                                cost_price=edit_cost,
                                volume=edit_volume,
                                alarm_percent=edit_alarm_pct,
                                alarm_price=edit_alarm_price,
                            )
                            db.add_stock(updated)
                            st.session_state[edit_key] = False
                            st.success(f"已更新 {pos.stock_name}")
                            st.rerun()
                    with col_cancel:
                        if st.form_submit_button("取消", width="stretch"):
                            st.session_state[edit_key] = False
                            st.rerun()
    else:
        st.info("暂无持仓，点击上方「添加自持个股」添加")


def render_evaluation_report():
    """渲染评估报告 Tab"""
    from evaluation.sector_evaluator import sector_evaluator

    # 日期范围选择 + 刷新按钮
    col_range, col_refresh = st.columns([4, 1])
    with col_range:
        range_option = st.selectbox(
            "日期范围",
            ["最近7天", "最近30天", "最近60天", "全部"],
            index=1,
            key="eval_range",
        )
    with col_refresh:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 刷新评估", width="stretch"):
            with st.spinner("正在评估历史预测..."):
                count = sector_evaluator.evaluate_all_pending()
            st.success(f"评估完成，更新了 {count} 条记录")
            st.rerun()

    # 计算日期范围
    today = datetime.now()
    range_days = {"最近7天": 7, "最近30天": 30, "最近60天": 60, "全部": None}
    days = range_days.get(range_option)
    start_date = (today - timedelta(days=days)).strftime("%Y-%m-%d") if days else None
    end_date = today.strftime("%Y-%m-%d") if days else None

    # 获取总体准确率
    summary = sector_evaluator.get_accuracy_summary(start_date, end_date)

    if all(summary[k]["total"] == 0 for k in ["t1", "t3", "t5"]):
        st.info("暂无评估数据，请先运行几天 Pipeline 积累数据后再查看")
        return

    # ========== 总体准确率 ==========
    st.markdown("---")
    col_t1, col_t3, col_t5 = st.columns(3)
    for col, key, label in [
        (col_t1, "t1", "T+1 准确率"),
        (col_t3, "t3", "T+3 准确率"),
        (col_t5, "t5", "T+5 准确率"),
    ]:
        with col:
            s = summary[key]
            st.metric(
                label=label,
                value=f"{s['accuracy']:.1f}%",
                delta=f"{s['correct']}/{s['total']}" if s['total'] > 0 else "无数据",
            )
            if s["pending"] > 0:
                st.caption(f"待评估: {s['pending']}")

    # ========== 准确率趋势 ==========
    st.markdown("---")
    st.subheader("📈 准确率趋势")
    trend_days = days if days else 60
    trend = sector_evaluator.get_daily_accuracy_trend(trend_days)

    if trend:
        dates = [t["date"] for t in trend]
        fig = go.Figure()
        for key, name, color in [
            ("t1_accuracy", "T+1", "#3b82f6"),
            ("t3_accuracy", "T+3", "#10b981"),
            ("t5_accuracy", "T+5", "#f59e0b"),
        ]:
            values = [t.get(key) for t in trend]
            fig.add_trace(go.Scatter(
                x=dates, y=values,
                mode="lines+markers",
                name=name,
                line=dict(color=color, width=2),
                marker=dict(size=5),
                connectgaps=True,
            ))
        fig.update_layout(
            yaxis_title="准确率 (%)",
            xaxis_title="预测日期",
            height=350,
            margin=dict(l=40, r=20, t=20, b=40),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        fig.update_yaxes(range=[0, 100], gridcolor="rgba(0,0,0,0.05)")
        fig.update_xaxes(gridcolor="rgba(0,0,0,0.05)")
        st.plotly_chart(fig, width="stretch")
    else:
        st.info("暂无趋势数据")

    # ========== 按置信度 / 按方向 分组 ==========
    st.markdown("---")
    col_conf, col_dir = st.columns(2)

    with col_conf:
        st.subheader("📊 按置信度分组")
        conf_data = sector_evaluator.get_accuracy_by_confidence(start_date, end_date)
        if conf_data:
            groups = [d["group"] for d in conf_data]
            fig_conf = go.Figure()
            for key, name, color in [
                ("t1_accuracy", "T+1", "#3b82f6"),
                ("t3_accuracy", "T+3", "#10b981"),
                ("t5_accuracy", "T+5", "#f59e0b"),
            ]:
                fig_conf.add_trace(go.Bar(
                    x=groups,
                    y=[d[key] for d in conf_data],
                    name=name,
                    marker_color=color,
                    text=[f"{d[key]:.0f}%" for d in conf_data],
                    textposition="auto",
                ))
            fig_conf.update_layout(
                barmode="group",
                yaxis_title="准确率 (%)",
                height=300,
                margin=dict(l=40, r=20, t=20, b=40),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
            )
            fig_conf.update_yaxes(range=[0, 100], gridcolor="rgba(0,0,0,0.05)")
            st.plotly_chart(fig_conf, width="stretch")
            for d in conf_data:
                st.caption(f"{d['group']}: {d['count']} 条预测")
        else:
            st.info("暂无数据")

    with col_dir:
        st.subheader("📊 按预测方向分组")
        dir_data = sector_evaluator.get_accuracy_by_direction(start_date, end_date)
        dir_labels = {"up": "上涨", "down": "下跌", "neutral": "中性"}
        if dir_data:
            directions = []
            for d in ["up", "down", "neutral"]:
                if d in dir_data and dir_data[d]["count"] > 0:
                    directions.append(d)
            if directions:
                labels = [dir_labels.get(d, d) for d in directions]
                fig_dir = go.Figure()
                for key, name, color in [
                    ("t1_accuracy", "T+1", "#3b82f6"),
                    ("t3_accuracy", "T+3", "#10b981"),
                    ("t5_accuracy", "T+5", "#f59e0b"),
                ]:
                    fig_dir.add_trace(go.Bar(
                        x=labels,
                        y=[dir_data[d][key] for d in directions],
                        name=name,
                        marker_color=color,
                        text=[f"{dir_data[d][key]:.0f}%" for d in directions],
                        textposition="auto",
                    ))
                fig_dir.update_layout(
                    barmode="group",
                    yaxis_title="准确率 (%)",
                    height=300,
                    margin=dict(l=40, r=20, t=20, b=40),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                )
                fig_dir.update_yaxes(range=[0, 100], gridcolor="rgba(0,0,0,0.05)")
                st.plotly_chart(fig_dir, width="stretch")
                for d in directions:
                    st.caption(f"{dir_labels.get(d, d)}: {dir_data[d]['count']} 条预测")
            else:
                st.info("暂无数据")
        else:
            st.info("暂无数据")

    # ========== 预测明细 ==========
    st.markdown("---")
    with st.expander("📝 预测明细", expanded=False):
        details = sector_evaluator.get_evaluation_details(limit=200)
        if details:
            rows = []
            for ev in details:
                def _fmt_correct(c, actual):
                    if c is None:
                        return "⏳"
                    return f"✅ ({actual:+.2f}%)" if c == 1 else f"❌ ({actual:+.2f}%)"

                dir_label = {"up": "上涨", "down": "下跌", "neutral": "中性"}.get(ev.direction, ev.direction)
                rows.append({
                    "日期": ev.prediction_date,
                    "板块": ev.sector_name,
                    "预测方向": dir_label,
                    "置信度": ev.confidence,
                    "T+1": _fmt_correct(ev.correct_t1, ev.actual_t1 or 0),
                    "T+3": _fmt_correct(ev.correct_t3, ev.actual_t3 or 0),
                    "T+5": _fmt_correct(ev.correct_t5, ev.actual_t5 or 0),
                })
            df = pd.DataFrame(rows)
            st.dataframe(df, width="stretch", height=400)
        else:
            st.info("暂无明细数据")


def _render_open_positions(simulator):
    """渲染当前持仓列表"""
    from db import Database
    _db = Database()
    open_trades = _db.get_open_trades()

    st.subheader("📦 当前持仓")
    if not open_trades:
        st.info("暂无持仓")
        return

    rows = []
    for t in open_trades:
        try:
            entry_dt = datetime.strptime(t.entry_date, "%Y-%m-%d")
            hold_days = (datetime.now() - entry_dt).days
        except:
            hold_days = 0

        signal_label = "强买" if t.signal == "strong_buy" else "买入"
        rows.append({
            "股票": f"{t.stock_name}({t.stock_code})",
            "板块": t.sector_name,
            "信号": signal_label,
            "置信度": f"{t.confidence:.0%}",
            "买入日期": t.entry_date,
            "买入价": f"{t.entry_price:.2f}",
            "持仓天数": hold_days,
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, width="stretch", hide_index=True)


def _render_recent_trades(simulator):
    """渲染最近交易操作记录"""
    from db import Database
    _db = Database()
    closed_trades = _db.get_trades_by_status("closed")

    st.markdown("---")
    st.subheader("📋 最近交易操作")

    if not closed_trades:
        st.info("暂无已完成的交易")
        return

    recent = sorted(closed_trades, key=lambda t: t.exit_date or "", reverse=True)[:20]

    exit_reason_map = {
        "stop_loss": "止损",
        "take_profit": "止盈",
        "max_hold": "到期",
    }

    rows = []
    for t in recent:
        reason_label = exit_reason_map.get(t.exit_reason, t.exit_reason or "–")
        signal_label = "强买" if t.signal == "strong_buy" else "买入"
        rows.append({
            "平仓日期": t.exit_date,
            "股票": f"{t.stock_name}({t.stock_code})",
            "板块": t.sector_name,
            "信号": signal_label,
            "买入价": f"{t.entry_price:.2f}",
            "卖出价": f"{t.exit_price:.2f}",
            "收益": f"{t.return_pct:+.2f}%",
            "持仓天数": t.holding_days,
            "平仓原因": reason_label,
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, width="stretch", hide_index=True)


def render_trade_evaluation():
    """渲染量化策略评估 Tab"""
    from evaluation.trade_simulator import trade_simulator

    # ========== 顶部: 日期范围 + 刷新按钮 ==========
    col_range, col_refresh = st.columns([4, 1])
    with col_range:
        range_option = st.selectbox(
            "日期范围",
            ["最近7天", "最近30天", "最近60天", "全部"],
            index=1,
            key="trade_eval_range",
        )
    with col_refresh:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 刷新模拟", width="stretch"):
            with st.spinner("正在执行模拟交易..."):
                result = trade_simulator.run_full_simulation()
            st.success(f"完成: 新建 {result['created']} 笔, 平仓 {result['closed']} 笔")
            st.rerun()

    # 计算日期范围
    today = datetime.now()
    range_days = {"最近7天": 7, "最近30天": 30, "最近60天": 60, "全部": None}
    days = range_days.get(range_option)
    start_date = (today - timedelta(days=days)).strftime("%Y-%m-%d") if days else None
    end_date = today.strftime("%Y-%m-%d") if days else None

    # 获取统计数据
    summary = trade_simulator.get_summary(start_date, end_date)

    if summary["total_trades"] == 0:
        st.info("暂无模拟交易数据，请先运行 Pipeline 生成买入信号后点击刷新")
        return

    # ========== 6列 st.metric ==========
    st.markdown("---")
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        st.metric("总交易", f"{summary['total_trades']}")
    with c2:
        wr = summary['win_rate']
        st.metric("胜率", f"{wr:.1f}%")
    with c3:
        avg_r = summary['avg_return']
        st.metric("平均收益", f"{avg_r:+.2f}%")
    with c4:
        total_r = summary['total_return']
        st.metric("总收益", f"{total_r:+.1f}%")
    with c5:
        pf = summary['profit_factor']
        pf_str = f"{pf:.2f}" if pf != float('inf') else "∞"
        st.metric("盈亏比", pf_str)
    with c6:
        st.metric("持仓中", f"{summary['open_trades']}")

    # ========== 当前持仓 ==========
    st.markdown("---")
    _render_open_positions(trade_simulator)

    # ========== 最近交易操作 ==========
    _render_recent_trades(trade_simulator)

    # ========== 累计收益曲线 ==========
    st.markdown("---")
    st.subheader("📈 累计收益曲线")
    pnl_data = trade_simulator.get_daily_pnl(days=days or 60)

    if pnl_data:
        dates = [d["date"] for d in pnl_data]
        cum_returns = [d["cumulative_return"] for d in pnl_data]

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=dates, y=cum_returns,
            mode="lines",
            fill="tozeroy",
            line=dict(color="#3b82f6", width=2),
            fillcolor="rgba(59, 130, 246, 0.1)",
            name="累计收益",
        ))
        fig.update_layout(
            yaxis_title="累计收益率 (%)",
            xaxis_title="日期",
            height=350,
            margin=dict(l=40, r=20, t=20, b=40),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        fig.update_yaxes(gridcolor="rgba(0,0,0,0.05)", zeroline=True, zerolinecolor="rgba(0,0,0,0.1)")
        fig.update_xaxes(gridcolor="rgba(0,0,0,0.05)")
        st.plotly_chart(fig, width="stretch")
    else:
        st.info("暂无收益曲线数据（需要有已平仓交易）")

    # ========== 按板块 / 按置信度 分组 ==========
    st.markdown("---")
    col_sector, col_conf = st.columns(2)

    with col_sector:
        st.subheader("📊 按板块分组")
        sector_data = trade_simulator.get_performance_by_sector(start_date, end_date)
        if sector_data:
            sectors = [d["sector"] for d in sector_data[:10]]
            fig_s = go.Figure()
            fig_s.add_trace(go.Bar(
                x=sectors,
                y=[d["win_rate"] for d in sector_data[:10]],
                name="胜率",
                marker_color="#3b82f6",
                text=[f"{d['win_rate']:.0f}%" for d in sector_data[:10]],
                textposition="auto",
            ))
            fig_s.add_trace(go.Bar(
                x=sectors,
                y=[d["avg_return"] for d in sector_data[:10]],
                name="平均收益",
                marker_color="#10b981",
                text=[f"{d['avg_return']:+.1f}%" for d in sector_data[:10]],
                textposition="auto",
            ))
            fig_s.update_layout(
                barmode="group",
                height=300,
                margin=dict(l=40, r=20, t=20, b=40),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
            )
            fig_s.update_yaxes(gridcolor="rgba(0,0,0,0.05)")
            st.plotly_chart(fig_s, width="stretch")
            for d in sector_data[:10]:
                st.caption(f"{d['sector']}: {d['count']} 笔")
        else:
            st.info("暂无数据")

    with col_conf:
        st.subheader("📊 按置信度分组")
        conf_data = trade_simulator.get_performance_by_confidence(start_date, end_date)
        if conf_data and any(d["count"] > 0 for d in conf_data):
            groups = [d["group"] for d in conf_data]
            fig_c = go.Figure()
            fig_c.add_trace(go.Bar(
                x=groups,
                y=[d["win_rate"] for d in conf_data],
                name="胜率",
                marker_color="#3b82f6",
                text=[f"{d['win_rate']:.0f}%" for d in conf_data],
                textposition="auto",
            ))
            fig_c.add_trace(go.Bar(
                x=groups,
                y=[d["avg_return"] for d in conf_data],
                name="平均收益",
                marker_color="#10b981",
                text=[f"{d['avg_return']:+.1f}%" for d in conf_data],
                textposition="auto",
            ))
            fig_c.update_layout(
                barmode="group",
                height=300,
                margin=dict(l=40, r=20, t=20, b=40),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
            )
            fig_c.update_yaxes(gridcolor="rgba(0,0,0,0.05)")
            st.plotly_chart(fig_c, width="stretch")
            for d in conf_data:
                st.caption(f"{d['group']}: {d['count']} 笔")
        else:
            st.info("暂无数据")

    # ========== 交易明细 ==========
    st.markdown("---")
    with st.expander("📝 交易明细", expanded=False):
        details = trade_simulator.get_trade_details(limit=200)
        if details:
            rows = []
            for t in details:
                exit_reason_map = {
                    "stop_loss": "止损",
                    "take_profit": "止盈",
                    "max_hold": "到期",
                }
                status_label = "持仓中" if t.status == "open" else "已平仓"
                rows.append({
                    "信号日期": t.trade_date,
                    "股票": f"{t.stock_name}({t.stock_code})",
                    "板块": t.sector_name,
                    "信号": "强买" if t.signal == "strong_buy" else "买入",
                    "置信度": f"{t.confidence:.2f}",
                    "买入价": f"{t.entry_price:.2f}" if t.entry_price else "-",
                    "卖出价": f"{t.exit_price:.2f}" if t.exit_price else "-",
                    "收益": f"{t.return_pct:+.2f}%" if t.status == "closed" else "-",
                    "持仓天数": str(t.holding_days) if t.status == "closed" else "-",
                    "平仓原因": exit_reason_map.get(t.exit_reason, t.exit_reason) if t.exit_reason else "-",
                    "状态": status_label,
                })
            df = pd.DataFrame(rows)
            st.dataframe(df, width="stretch", height=400)
        else:
            st.info("暂无交易明细")


if __name__ == "__main__":
    main()
