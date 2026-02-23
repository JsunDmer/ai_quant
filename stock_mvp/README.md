# Stock MVP - 股民投资助手

基于每日收盘模式的决策辅助工具。

## 功能

- **市场总览**: 收盘后市场快照（指数、涨跌分布、成交额、北向资金、快讯）
- **板块分析**: 资金+估值+趋势评分，输出强推/关注/观望分层建议
- **量化策略**: 板块内股票的买入/卖出信号，量化+AI综合

## 快速开始

```bash
cd stock_mvp
pip install -r requirements.txt
streamlit run app.py
```

## 触发分析

两种方式触发收盘分析：

1. **页面按钮**: 点击「🚀 执行收盘分析」按钮
2. **CLI 命令**:
   ```bash
   python -m pipeline run-post-close --date 2024-01-15
   ```

## 配置

在 `.env` 文件中配置：

```
LLM_API_KEY=your_api_key
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
```

## 技术栈

- Streamlit (UI)
- AKShare (行情数据)
- SQLite (本地存储)
- OpenAI 兼容接口 (AI 分析)

## 目录结构

```
stock_mvp/
├── app.py              # 主应用
├── pipeline.py         # 收盘流水线
├── market_data.py      # 市场数据采集
├── sector_data.py      # 板块评分
├── quant_strategy.py   # 量化信号
├── db.py               # 数据库
├── config.py           # 配置
└── tests/             # 测试
```
