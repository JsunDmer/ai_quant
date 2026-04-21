# 项目调整实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 调整项目：移除量化策略模块（API调用相关逻辑），增加个股大资金流向数据，添加详细日志

**Architecture:** 
1. 移除 `strategy/quant_strategy.py` 及相关调用（pipeline.py 中的信号生成逻辑）
2. 保留数据采集层（market_data.py, stock_data.py, sector_data.py, news_collector.py）
3. 保留 AI 分析层（ai_news_generator.py, ai_sector_analyzer.py），因为它们是分析核心，非"交易策略"
4. 在 stock_data.py 中增加个股大资金流向接口
5. 在各数据获取模块中添加详细日志

**Tech Stack:** Python, AKShare, Streamlit, SQLite

---

### Task 1: 移除量化策略模块

**Files:**
- Delete: `stock_mvp/strategy/quant_strategy.py`
- Modify: `stock_mvp/pipeline.py:260-344` (移除 Step 4-5 的信号生成逻辑)
- Modify: `stock_mvp/app.py:727-728` (移除 Tab 5 量化策略评估)

**Step 1: 删除 quant_strategy.py 文件**

```bash
rm stock_mvp/strategy/quant_strategy.py
```

**Step 2: 修改 pipeline.py，移除信号生成逻辑**

修改 `run_post_close_pipeline` 函数，移除：
- Step 4: 候选股票筛选 (lines 266-288)
- Step 5: 信号生成 (lines 290-343)

保留 Step 1-3:
- Step 1: 市场快照采集
- Step 1.5: 板块当日涨跌幅记录
- Step 2: AI新闻生成
- Step 3: AI板块分析

更新 pipeline 步骤注释为 Step 1/3, Step 2/3, Step 3/3

**Step 3: 修改 app.py，移除量化策略评估 Tab**

将 Tab 5 从 5 个减少到 4 个：
```python
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 市场分析", "🎯 板块分析", "💰 个股分析", "📋 评估报告"
])
```

移除 `render_trade_evaluation()` 函数调用

**Step 4: 运行测试验证**

Run: `cd stock_mvp && python -c "from pipeline import run_post_close_pipeline; print('Pipeline import OK')"`
Expected: 导入成功，无 quant_strategy 引用错误

**Step 5: Commit**

```bash
git add stock_mvp/strategy/ stock_mvp/pipeline.py stock_mvp/app.py
git commit -m "refactor: remove quant strategy module and signal generation"
```

---

### Task 2: 增加个股大资金流向数据接口

**Files:**
- Modify: `stock_mvp/data/stock_data.py` (增加方法)
- Test: `tests/test_stock_capital_flow.py` (新建)

**Step 1: 添加大资金流向方法**

在 `StockData` 类中添加方法：

```python
def get_stock_capital_flow(self, stock_code: str) -> Dict[str, Any]:
    """
    获取个股大资金流向（单日）
    
    Returns:
        {
            'main_inflow': float,    # 主力净流入(万元)
            'main_inflow_pct': float, # 主力净流入占比(%)
            'super_inflow': float,    # 超大单净流入(万元)
            'large_inflow': float,    # 大单净流入(万元)
            'medium_inflow': float,   # 中单净流入(万元)
            'small_inflow': float,    # 小单净流入(万元)
            'trade_date': str         # 交易日期
        }
    """
    try:
        # 使用 akshare 的个股资金流向接口
        df = ak.stock_individual_fund_flow_em(symbol=stock_code, market="主板")
        if df is None or df.empty:
            return self._empty_capital_flow()
        
        latest = df.iloc[0]
        return {
            'main_inflow': float(latest.get('主力净流入', 0)) if pd.notna(latest.get('主力净流入')) else 0,
            'main_inflow_pct': float(latest.get('主力净流入占比', 0)) if pd.notna(latest.get('主力净流入占比')) else 0,
            'super_inflow': float(latest.get('超大单净流入', 0)) if pd.notna(latest.get('超大单净流入')) else 0,
            'large_inflow': float(latest.get('大单净流入', 0)) if pd.notna(latest.get('大单净流入')) else 0,
            'medium_inflow': float(latest.get('中单净流入', 0)) if pd.notna(latest.get('中单净流入')) else 0,
            'small_inflow': float(latest.get('小单净流入', 0)) if pd.notna(latest.get('小单净流入')) else 0,
            'trade_date': str(latest.get('日期', ''))
        }
    except Exception as e:
        print(f"[StockData] 获取个股资金流向失败 {stock_code}: {e}")
        return self._empty_capital_flow()

def _empty_capital_flow(self) -> Dict[str, Any]:
    """返回空资金流向数据"""
    return {
        'main_inflow': 0, 'main_inflow_pct': 0,
        'super_inflow': 0, 'large_inflow': 0,
        'medium_inflow': 0, 'small_inflow': 0,
        'trade_date': ''
    }
```

**Step 2: 编写测试**

创建 `tests/test_stock_capital_flow.py`:

```python
import pytest
from data.stock_data import StockData

def test_get_stock_capital_flow():
    """测试获取个股资金流向"""
    stock = StockData()
    # 测试常用股票
    result = stock.get_stock_capital_flow("600519")  # 茅台
    assert isinstance(result, dict)
    assert 'main_inflow' in result
    assert 'main_inflow_pct' in result
    print(f"茅台资金流向: {result}")

def test_get_stock_capital_flow_empty():
    """测试获取不存在股票的资金流向"""
    stock = StockData()
    result = stock.get_stock_capital_flow("999999")
    assert result['main_inflow'] == 0
```

**Step 3: 运行测试**

Run: `cd stock_mvp && python -m pytest tests/test_stock_capital_flow.py -v`
Expected: PASS (或 SKIP 如果 API 不可用)

**Step 4: Commit**

```bash
git add stock_mvp/data/stock_data.py stock_mvp/tests/test_stock_capital_flow.py
git commit -m "feat: add stock capital flow data interface"
```

---

### Task 3: 添加股市数据获取日志

**Files:**
- Modify: `stock_mvp/data/stock_data.py` (增加日志)
- Modify: `stock_mvp/data/market_data.py` (增加日志)
- Modify: `stock_mvp/data/sector_data.py` (增加日志)
- Modify: `stock_mvp/data/news_collector.py` (增加日志)

**Step 1: 为 stock_data.py 添加日志**

在关键方法添加日志：
- `_get_spot_data()` - 添加获取开始/完成日志
- `get_realtime_quote()` - 添加获取成功/失败日志
- `get_kline_data()` - 添加获取开始/完成日志
- `get_stock_capital_flow()` - 添加获取日志

示例格式：
```python
# 获取行情数据
print(f"[StockData] 获取实时行情 {stock_code} ...")
# ... 获取逻辑 ...
print(f"[StockData] 获取实时行情 {stock_code} 完成，价: {price:.2f}")
```

**Step 2: 为 market_data.py 添加日志**

在关键方法添加日志：
- `get_indices()` - 添加日志
- `get_market_breadth()` - 添加日志
- `get_turnover()` - 添加日志
- `collect_post_close_snapshot()` - 添加整体进度日志

**Step 3: 为 sector_data.py 添加日志**

在关键方法添加日志：
- `get_sector_list()` - 添加日志
- `get_sector_stocks()` - 添加日志
- `get_sector_fund_flow()` - 添加日志

**Step 4: 为 news_collector.py 添加日志**

在关键方法添加日志：
- `collect_all_news()` - 添加各源采集状态日志
- 单个新闻源方法添加日志

**Step 5: 运行验证**

Run: `cd stock_mvp && python -c "from data import stock_data; stock_data.get_realtime_quote('600519')"`
Expected: 看到日志输出

**Step 6: Commit**

```bash
git add stock_mvp/data/stock_data.py stock_mvp/data/market_data.py stock_mvp/data/sector_data.py stock_mvp/data/news_collector.py
git commit -m "chore: add detailed logging for stock data acquisition"
```

---

### Task 4: 整体验证

**Step 1: 运行 pipeline 验证**

Run: `cd stock_mvp && python -c "from pipeline import run_post_close_pipeline; result = run_post_close_pipeline(); print(f'Status: {result[\"status\"]}')"`
Expected: 运行成功，状态 ok 或 degraded（如果某些数据源失败）

**Step 2: 启动 UI 验证**

Run: `cd stock_mvp && timeout 10 streamlit run app.py --server.headless=true 2>&1 | head -20`
Expected: UI 启动成功，无报错

**Step 3: Commit**

```bash
git add -A
git commit -m "chore: project refactor complete - remove quant strategy, add capital flow, enhance logging"
```

---

## 执行选项

**1. Subagent-Driven (this session)** - 我调度子任务逐个完成，任务间进行代码审查，快速迭代

**2. Parallel Session (separate)** - 在新会话中使用 executing-plans，批量执行任务并设置检查点

请选择你偏好的执行方式？