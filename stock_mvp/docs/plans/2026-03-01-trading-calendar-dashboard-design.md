# 交易日历 + 本地定时并行 + 决策仪表盘 设计

## 目标

- A 股交易日判断替换“仅排除周末”的逻辑，节假日可正确回退到最近交易日。
- 定时与手动并行：保留本地 Streamlit 定时触发，CLI 继续支持手动执行，且同日不重复执行。
- 决策仪表盘报告结构化，UI/CLI/未来推送复用同一结构。

## 范围

- 修改 `pipeline.py` 的交易日与报告产出逻辑。
- 修改 `app.py` 的定时触发逻辑与报告展示。
- 新增轻量报告结构（不新增数据库表）。

## 设计方案（采用）

**轻量内聚方案（推荐）**

- 交易日历：引入 `exchange-calendars` 的 A 股日历（XSHG），提供 `is_trading_day()` 和 `latest_trading_day()`，失败时回退到“仅排除周末”。
- 定时并行：保留 Streamlit 前端定时触发，CLI 继续手动触发；定时运行前判断“当日是否已执行”，避免重复跑。
- 决策仪表盘：在 `run_post_close_pipeline()` 生成结构化 `dashboard_report`，UI/CLI 直接渲染该结构，后续推送复用。

## 设计细节

### 交易日历判断

- 交易日判断基于 `exchange-calendars` 的 A 股日历（XSHG）。
- 当传入日期为非交易日时，回退到最近交易日，并在 CLI 输出中标明。
- 若日历库不可用，则退回现有“排除周末”逻辑，保证不阻塞运行。

### 定时与手动并行

- **本地定时**：保留 `app.py` 中的定时触发设置（收盘时间）。
- **CLI 手动**：`python -m pipeline run-post-close --date` 继续有效。
- **防重复**：若当日已有 `market_snapshots` 或 `ai_news` 记录，则跳过完整分析，仅做提示。

### 决策仪表盘报告结构

- 在 `pipeline.run_post_close_pipeline()` 生成 `dashboard_report`，包含：
  - `headline`：一句话结论
  - `summary`：信号数量、板块数量等统计
  - `action_points`：买入/止损/目标点位（可空）
  - `risk_alerts`：风险提示列表
  - `checklist`：条件清单（✅⚠️❌）
- UI 与 CLI 仅负责渲染，不再重复拼装文案。

## 错误处理

- 日历失败或网络错误时退回周末逻辑，打印降级提示。
- 数据缺失时 dashboard_report 允许为空结构，不影响主流程。

## 测试策略

- 单测：非交易日输入应回退到最近交易日。
- CLI：传入非交易日时输出回退日期，并保持流程成功完成。
