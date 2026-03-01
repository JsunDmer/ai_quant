# Stock MVP - 股民投资助手

基于 AI + 量化双引擎的 A 股投资决策辅助工具。采集多源财经新闻，AI 分析板块方向，量化评分筛选个股，生成买卖信号。

## 技术架构

```
┌─────────────────────────────────────────────────────┐
│                   Streamlit UI                       │
│  ┌─────────────┐ ┌─────────────┐ ┌───────────────┐  │
│  │  市场分析    │ │  板块分析    │ │   个股分析     │  │
│  │ 新闻卡片网格 │ │ AI方向预测  │ │ 买入/卖出信号  │  │
│  │ 7大指数     │ │ 量化评分    │ │ 自持股票管理   │  │
│  └─────────────┘ └─────────────┘ └───────────────┘  │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│                Pipeline 流水线                        │
│                                                      │
│  ① 市场快照采集 → ② AI新闻结构化 → ③ AI板块分析     │
│  → ④ 量化板块评分 → ⑤ 候选筛选 + 信号生成            │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│              数据层 & 外部服务                         │
│  ┌──────────┐  ┌──────────┐  ┌───────────────────┐  │
│  │  SQLite  │  │ AKShare  │  │ LLM (DeepSeek)    │  │
│  │  11张表  │  │ A股行情   │  │ OpenAI兼容接口     │  │
│  └──────────┘  └──────────┘  └───────────────────┘  │
│  ┌──────────────────────────────────────────────┐   │
│  │  9源新闻采集 (DuckDuckGo/东方财富/新浪/AI     │   │
│  │  Agent/第一财经/澎湃/界面/财新/观察者网)       │   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

## Pipeline 核心链路

```
原始新闻 (9源)
    │
    ▼
Step 1: 市场快照采集 ──→ market_snapshots 表
    │   指数/涨跌分布/成交额/北向资金/新闻
    ▼
Step 2: AI 新闻结构化 ──→ ai_news 表
    │   LLM 提取: 标题/摘要/分类/情绪/关键词/关联板块/重要性
    ▼
Step 3: AI 板块分析 ──→ ai_sector_analysis 表
    │   LLM 判断: 板块方向(up/down) + 概率分配 + 置信度 + 理由
    ▼
Step 4: 量化板块评分 ──→ sector_recommendations 表
    │   资金流向(30分) + 涨跌趋势(25分) → strong_recommend/watch/hold
    ▼
Step 5: 候选筛选 + 信号生成 ──→ stock_signals 表
        从 strong_recommend 板块选股 → 60日K线 → 技术分析 → 买卖信号
```

### AI 分析链路

**新闻结构化** (`ai_news_generator.py`): 原始新闻 → LLM → 结构化 JSON (title/summary/sentiment/keywords/related_sectors/importance)

**板块方向预测** (`ai_sector_analyzer.py`): 结构化新闻 → LLM → 每个板块的 direction + score_up/score_down + confidence + reasons。要求必须基于新闻内容，不能凭空捏造。

### 量化分析链路

**板块评分** (`sector_data.py`): 资金流向 (净流入/流出) + 当日涨跌幅趋势，满分 55 分，≥40 强推荐。

**个股技术分析** (`quant_strategy.py`):
- 均线系统: MA5/MA10/MA20 多空排列、金叉死叉
- RSI 指标: 超买(>70) / 超卖(<30)
- 量价关系: 放量上涨/下跌、缩量
- 价格动量: 5日/10日涨跌幅
- 综合评分 -100~+100 → strong_buy / buy / hold / sell / strong_sell

## UI 布局

页面顶部: 标题 + 执行分析按钮 + 设置面板 (API Key / 自动刷新 / 定时分析 / AI开关 / 新闻源开关)

| Tab | 内容 |
|-----|------|
| 市场分析 | 新闻卡片网格 (情绪颜色+摘要+关联板块) + 7大指数 + 涨跌分布 + 成交额 |
| 板块分析 | 左: AI预估上涨板块 (方向+置信度+推荐个股) / 右: AI预估下跌板块 |
| 个股分析 | 左: 预估上涨个股 (买入信号) / 右: 预估下跌个股 (仅自持股票) + 我的持仓管理 |

## 数据库表

| 表 | 用途 |
|----|------|
| market_snapshots | 每日市场快照 |
| ai_news | AI 结构化新闻 (sentiment/keywords/importance) |
| ai_sector_analysis | AI 板块方向分析 (direction/score_up/score_down/confidence) |
| sector_recommendations | 量化板块评分 (score/bucket) |
| stock_signals | 个股买卖信号 (signal/confidence/factors) |
| sector_stocks | 板块成分股缓存 (当天首次拉取后缓存) |
| followed_stocks | 用户自持个股 |
| analysis_records | AI 分析历史 |
| alert_records | 价格报警记录 |

## 目录结构

```
stock_mvp/
├── app.py                 # Streamlit UI 主入口
├── pipeline.py            # 收盘分析流水线编排
├── market_data.py         # 市场数据采集 (指数/涨跌/成交额/北向资金)
├── news_collector.py      # 9源新闻采集 (DDGS/东财/新浪/AI/第一财经/澎湃/界面/财新/观察者网)
├── sector_data.py         # 板块评分与个股筛选 (带 DB 缓存)
├── stock_data.py          # 个股行情与K线数据
├── quant_strategy.py      # 量化策略 (均线/RSI/量价/动量)
├── ai_news_generator.py   # AI 结构化新闻生成
├── ai_sector_analyzer.py  # AI 板块方向分析
├── db.py                  # SQLite ORM
├── config.py              # 配置管理 (.env)
├── start.sh               # 启动脚本
└── tests/                 # 测试
    └── test_news_collector.py
```

## 快速开始

```bash
cd stock_mvp
pip install -r requirements.txt
cp .env.example .env  # 填入 LLM API Key
streamlit run app.py
```

## 配置

在 `.env` 中配置:

```
LLM_API_KEY=your_api_key
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
```

## 触发分析

- **页面按钮**: 点击「🚀 执行分析」
- **自动刷新**: 设置面板开启，每 N 分钟刷新市场数据
- **定时分析**: 设置收盘时间，自动执行完整 Pipeline
- **CLI**: `python -m pipeline run-post-close --date 2024-01-15`

## 技术栈

- **UI**: Streamlit
- **数据**: AKShare (A股行情) + 东方财富 API (单股查询/搜索)
- **新闻**: 9 源采集 (requests + BeautifulSoup4 + duckduckgo-search)
- **AI**: OpenAI 兼容接口 (默认 DeepSeek)
- **存储**: SQLite
- **可视化**: Plotly + HTML 卡片网格
