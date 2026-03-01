# AI Quant - 股民投资助手

## 项目概述
基于 AI Agent 采集市场信息，AI 分析板块，给出板块核心个股判断的投资辅助工具。

- **框架**: Streamlit (Python)
- **数据源**: AKShare (A股行情), 多源新闻采集 (news_collector.py)
- **AI**: OpenAI 兼容接口 (默认 DeepSeek)
- **数据库**: SQLite (`stock_mvp/stock_mvp.db`)
- **入口**: `stock_mvp/app.py`

## 项目结构

```
stock_mvp/
├── app.py                     # Streamlit UI 主入口
├── pipeline.py                # 收盘分析流水线编排
├── config.py                  # 配置管理 (.env)
├── db.py                      # SQLite 数据库 ORM
├── data/                      # 数据采集层
│   ├── __init__.py
│   ├── market_data.py         # 市场数据采集 (指数/涨跌/成交额/北向资金)
│   ├── sector_data.py         # 板块评分与个股筛选 (带 DB 缓存)
│   ├── stock_data.py          # 个股行情与K线数据 (AKShare)
│   ├── news_collector.py      # 多源新闻采集 (9个RSS/网页源)
│   └── akshare_patch.py       # AKShare 接口兼容补丁
├── ai/                        # AI 分析层
│   ├── __init__.py
│   ├── news_generator.py      # AI 结构化新闻生成
│   └── sector_analyzer.py     # AI 板块方向分析
├── evaluation/                # 预测评估层
│   ├── __init__.py
│   ├── sector_evaluator.py    # 板块预测评估引擎 (T+1/T+3/T+5 准确率)
│   └── trade_simulator.py     # 模拟交易引擎 (建仓/平仓/收益统计)
├── strategy/                  # 量化策略层
│   ├── __init__.py
│   └── quant_strategy.py      # 量化策略 (均线/RSI/量价/动量技术分析)
├── tests/
└── start.sh                   # 启动脚本
```

## UI 布局 (五大模块)

页面顶部: 标题 + 执行分析按钮 + 可展开设置面板 (API Key/定时任务/新闻源/AI开关)
不使用 Streamlit sidebar，设置用 st.expander 实现。
顶部栏/deploy按钮/hamburger菜单全部通过 CSS 隐藏。

### Tab 1: 市场分析
- **上方**: 新闻热点 (HTML卡片网格，颜色=情绪) + AI新闻摘要列表
- **下方**: 7大市场指数 + 市场广度 + 北向资金

### Tab 2: 板块分析
- **左列**: 预估上涨板块 (AI方向+评分+置信度+推荐个股)
- **右列**: 预估下跌板块

### Tab 3: 个股分析
- **左列**: 预估上涨个股 (买入信号，按置信度排序)
- **右列**: 预估下跌个股 (卖出信号)
- **底部**: 我的持仓 (支持添加/删除自持个股)

### Tab 4: 评估报告
- **顶部**: 日期范围选择 + 刷新评估按钮
- **准确率**: T+1/T+3/T+5 三列 st.metric
- **趋势图**: Plotly 折线图 (蓝/绿/黄三条线)
- **分组统计**: 按置信度分组 + 按预测方向分组 (Plotly 条形图)
- **明细**: 预测明细表 (st.dataframe, 默认收起)

### Tab 5: 量化策略评估
- **顶部**: 日期范围选择 + 刷新模拟按钮
- **指标**: 总交易/胜率/平均收益/总收益/盈亏比/持仓中 (6列 st.metric)
- **曲线**: 累计收益曲线 (Plotly 面积图)
- **分组**: 按板块分组 + 按置信度分组 (Plotly 条形图)
- **明细**: 交易明细表 (st.dataframe, 默认收起)

## Pipeline 流程 (执行分析)

```
Step 1:   市场快照采集 → market_snapshots 表
          (指数/涨跌/成交额/北向资金，新闻采集已暂停)
Step 1.5: 板块涨跌幅采集 → sector_daily_performance 表
          (从AKShare获取板块列表及涨跌幅，板块名列表供后续AI分析复用)
Step 2:   AI新闻生成 → ai_news 表
        (将原始新闻发给LLM生成结构化摘要，当前因无新闻源会跳过)
Step 3: AI板块分析 → ai_sector_analysis 表
        (基于AI新闻判断板块方向/概率/置信度)
Step 4: 板块评分推荐 → sector_recommendations 表
        (资金流向+涨跌幅趋势打分，分为strong_recommend/watch/hold)
Step 5: 候选股票筛选 + 信号生成 → stock_signals 表
        (从强推荐板块选股 → 拉60日K线 → 技术分析 → 生成买卖信号)
```

已移除: Step 6 AI市场分析 (ai_analysis.py 的 analyze_market)

## 数据库表

| 表名 | 用途 |
|------|------|
| `market_snapshots` | 每日市场快照 |
| `sector_recommendations` | 板块评分推荐 |
| `stock_signals` | 个股买卖信号 |
| `ai_news` | AI结构化新闻 (title/summary/sentiment/keywords/source_url) |
| `ai_sector_analysis` | AI板块方向分析 (direction/score_up/score_down/confidence) |
| `ai_analysis_results` | AI市场分析结果 (已停用) |
| `sector_stocks` | 板块成分股缓存 (当天首次拉取后缓存，避免重复请求akshare) |
| `followed_stocks` | 用户自持个股 |
| `analysis_records` | AI分析历史记录 |
| `alert_records` | 价格报警记录 |
| `sector_daily_performance` | 板块每日实际涨跌幅 (Pipeline Step 1.5 写入) |
| `prediction_evaluations` | 预测评估结果 (T+1/T+3/T+5 准确率) |
| `simulated_trades` | 模拟交易记录 (建仓/平仓/收益率/止损止盈) |

## 关键设计决策

1. **新闻展示用 HTML 卡片网格**: 每张卡片=一条新闻，颜色=情绪(绿利好/红利空/灰中性)
2. **新闻列表优先 AI 结构化新闻**: 显示情绪图标+标题(带超链接)+摘要+分类+重要性+关联板块
3. **板块成分股 DB 缓存**: 同一天同一板块只请求一次 akshare，后续走 sector_stocks 表缓存
4. **AI新闻生成 prompt 保留原始 URL**: 要求 AI 在输出中保留 source_url 字段
5. **不使用 Streamlit sidebar**: 因 header/deploy/sidebar-toggle 绑定无法分离，改用页面顶部 expander
6. **多源新闻采集**: news_collector.py 支持 9 个 RSS/网页源自动采集
7. **板块名称统一**: Pipeline Step 1.5 获取AKShare板块名列表，传给AI prompt约束输出，确保预测与实际数据的板块名精确匹配
8. **预测评估引擎**: 自动回溯AI板块预测，计算T+1/T+3/T+5累计涨跌幅，判断方向正确性

## 已知缺失/暂停模块

- AI市场分析 (Step 6) - 已从 pipeline 移除，`ai_analysis_results` 表保留兼容历史数据

## CSS 主题

FinTech 浅色主题，CSS 变量定义在 app.py 顶部:
- 字体: Noto Sans SC (中文) + JetBrains Mono (数据)
- 颜色: 绿(#10b981)=利好, 红(#ef4444)=利空, 蓝(#3b82f6)=主色
- 板块/个股卡片: section-header-up(绿) / section-header-down(红) 区域标题

## 语言
- 用中文回答