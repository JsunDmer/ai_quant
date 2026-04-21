# Data Access Enhancement Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add multi-source data fallback, standardized K-line fields, and configuration-driven source priority without changing public APIs.

**Architecture:** Keep `StockData` as the public interface while adding a lightweight internal source manager and normalization helpers. Use config entries to define priority order and ensure all downstream consumers depend only on normalized columns.

**Tech Stack:** Python, pandas, akshare, (optional) efinance/tushare

---

### Task 1: Add configuration for data source priority

**Files:**
- Modify: `config.py`

**Step 1: Write the failing test**

```python
def test_data_source_priority_defaults():
    from config import Config
    cfg = Config()
    assert cfg.DATA_SOURCE_PRIORITY
    assert cfg.REALTIME_SOURCE_PRIORITY
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py::test_data_source_priority_defaults -v`
Expected: FAIL with AttributeError (missing fields)

**Step 3: Write minimal implementation**

Add to `Config`:
- `DATA_SOURCE_PRIORITY` (default `akshare,efinance,tushare`)
- `REALTIME_SOURCE_PRIORITY` (default `akshare_em,akshare_sina,akshare_tencent`)

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_config.py::test_data_source_priority_defaults -v`
Expected: PASS

**Step 5: Commit**

```bash
git add config.py tests/test_config.py
git commit -m "feat: add data source priority config"
```

### Task 2: Add normalization helpers for K-line data

**Files:**
- Modify: `data/stock_data.py`
- Test: `tests/test_stock_data_normalization.py`

**Step 1: Write the failing test**

```python
import pandas as pd
from data.stock_data import StockData

def test_normalize_kline_columns():
    df = pd.DataFrame({
        "日期": ["2024-01-01"],
        "开盘": [10],
        "收盘": [12],
        "最高": [13],
        "最低": [9],
        "成交量": [1000],
        "成交额": [10000],
        "涨跌幅": [1.2],
    })
    normalized = StockData()._normalize_kline_df(df)
    assert set(["date","open","high","low","close","volume","amount","pct_chg"]).issubset(normalized.columns)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_stock_data_normalization.py::test_normalize_kline_columns -v`
Expected: FAIL with AttributeError (missing _normalize_kline_df)

**Step 3: Write minimal implementation**

Implement `_normalize_kline_df()` in `StockData`:
- Rename known columns from common sources
- Ensure required columns exist
- Convert types, parse date, sort

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_stock_data_normalization.py::test_normalize_kline_columns -v`
Expected: PASS

**Step 5: Commit**

```bash
git add data/stock_data.py tests/test_stock_data_normalization.py
git commit -m "feat: normalize kline data columns"
```

### Task 3: Add multi-source fetch order for K-line data

**Files:**
- Modify: `data/stock_data.py`
- Test: `tests/test_stock_data_fallback.py`

**Step 1: Write the failing test**

```python
from data.stock_data import StockData

def test_kline_fallback_order(monkeypatch):
    sd = StockData()
    calls = []

    def fail_first(*args, **kwargs):
        calls.append("akshare")
        raise RuntimeError("fail")

    def succeed_second(*args, **kwargs):
        calls.append("efinance")
        return sd._normalize_kline_df(sd._fake_kline_df())

    monkeypatch.setattr(sd, "_fetch_kline_akshare", fail_first)
    monkeypatch.setattr(sd, "_fetch_kline_efinance", succeed_second)

    df = sd.get_kline_data("600519", days=10)
    assert not df.empty
    assert calls == ["akshare", "efinance"]
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_stock_data_fallback.py::test_kline_fallback_order -v`
Expected: FAIL (methods not present)

**Step 3: Write minimal implementation**

Add in `StockData`:
- `_fetch_kline_akshare`, `_fetch_kline_efinance`, `_fetch_kline_tushare`
- `get_kline_data()` uses config priority list and retries per source
- Provide `_fake_kline_df()` for tests (small utility)

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_stock_data_fallback.py::test_kline_fallback_order -v`
Expected: PASS

**Step 5: Commit**

```bash
git add data/stock_data.py tests/test_stock_data_fallback.py
git commit -m "feat: add kline multi-source fallback"
```

### Task 4: Normalize realtime quote outputs

**Files:**
- Modify: `data/stock_data.py`
- Test: `tests/test_realtime_quote_normalization.py`

**Step 1: Write the failing test**

```python
from data.stock_data import StockData

def test_realtime_quote_has_standard_fields():
    sd = StockData()
    quote = sd._normalize_quote_row({
        "代码": "600519",
        "名称": "贵州茅台",
        "最新价": 100.0,
        "今开": 99.0,
        "最高": 101.0,
        "最低": 98.0,
        "昨收": 95.0,
        "成交量": 1000,
        "成交额": 100000,
        "涨跌幅": 1.0,
        "换手率": 0.5,
    })
    assert quote["code"] == "600519"
    assert "price" in quote and "volume" in quote
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_realtime_quote_normalization.py::test_realtime_quote_has_standard_fields -v`
Expected: FAIL (missing normalize method)

**Step 3: Write minimal implementation**

Add `_normalize_quote_row()` and refactor `get_realtime_quote/get_batch_quotes` to use it.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_realtime_quote_normalization.py::test_realtime_quote_has_standard_fields -v`
Expected: PASS

**Step 5: Commit**

```bash
git add data/stock_data.py tests/test_realtime_quote_normalization.py
git commit -m "feat: standardize realtime quote output"
```

### Task 5: Verify pipeline integrity

**Files:**
- None (verification only)

**Step 1: Run pipeline smoke check**

Run: `python -m pipeline run-post-close --date 2024-01-15`
Expected: Process completes without crashing and writes data into sqlite

**Step 2: Commit**

```bash
git status
```

---

Plan complete and saved to `docs/plans/2026-02-28-data-access-implementation-plan.md`. Two execution options:

1. Subagent-Driven (this session) - I dispatch fresh subagent per task, review between tasks, fast iteration
2. Parallel Session (separate) - Open new session with executing-plans, batch execution with checkpoints

Which approach?
