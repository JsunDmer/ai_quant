# React + FastAPI 前端重构 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用 Vite + React(TS) + ECharts 替换现有 Streamlit UI，并新增 FastAPI API 层（含“执行分析”任务触发 + 轮询），最终实现侧边栏主导航（四大模块）+ 主题切换（浅/深/系统）。

**Architecture:** 在 `stock_mvp` 内新增 FastAPI（复用现有 `pipeline/db/data`），以 in-memory job store 支持任务轮询；前端独立 `frontend/` 工程，通过 REST 拉取数据与触发任务，UI 令牌沿用 FinTech Light，并新增 dark token 覆盖与 ECharts 换肤策略。

**Tech Stack:** FastAPI, Uvicorn, httpx/pytest；Vite, React, TypeScript, ECharts

---

## 文件结构（将被创建/修改）

**Backend (Python)**
- Create: `stock_mvp/api/__init__.py`
- Create: `stock_mvp/api/app.py`（FastAPI app 入口）
- Create: `stock_mvp/api/schemas.py`（响应 DTO）
- Create: `stock_mvp/api/jobs.py`（in-memory job store + 任务状态机）
- Create: `stock_mvp/api/routes/health.py`
- Create: `stock_mvp/api/routes/market.py`
- Create: `stock_mvp/api/routes/sectors.py`
- Create: `stock_mvp/api/routes/signals.py`
- Create: `stock_mvp/api/routes/evaluation.py`
- Create: `stock_mvp/api/routes/jobs.py`
- Modify: `stock_mvp/requirements.txt`（新增 fastapi/uvicorn/httpx 等）
- (Optional) Modify: `stock_mvp/start.sh`（移除强制 venv，或提供 conda base 友好启动方式）

**Backend tests**
- Create: `stock_mvp/tests/test_api_health.py`
- Create: `stock_mvp/tests/test_api_jobs.py`
- Create: `stock_mvp/tests/test_api_market.py`（最少 1 个只读接口覆盖）

**Frontend**
- Create: `frontend/package.json`（Vite + React + TS）
- Create: `frontend/vite.config.ts`（开发时代理到 FastAPI）
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/app/App.tsx`
- Create: `frontend/src/app/layout/AppLayout.tsx`
- Create: `frontend/src/app/layout/AppSidebar.tsx`
- Create: `frontend/src/app/layout/PageHeader.tsx`
- Create: `frontend/src/styles/tokens.css`（light/dark token）
- Create: `frontend/src/styles/global.css`
- Create: `frontend/src/theme/theme.ts`（主题模式：light/dark/system；localStorage；prefers-color-scheme）
- Create: `frontend/src/api/client.ts`（fetch 封装）
- Create: `frontend/src/api/types.ts`
- Create: `frontend/src/pages/MarketPage.tsx`
- Create: `frontend/src/pages/SectorsPage.tsx`
- Create: `frontend/src/pages/SignalsPage.tsx`
- Create: `frontend/src/pages/EvaluationPage.tsx`
- Create: `frontend/src/components/MetricCard.tsx`
- Create: `frontend/src/components/Alert.tsx`
- Create: `frontend/src/components/LoadingSkeleton.tsx`
- Create: `frontend/src/charts/echartsTheme.ts`
- Create: `frontend/src/charts/EChart.tsx`（封装实例创建/销毁与换肤）

---

### Task 1: 后端 FastAPI 骨架与健康检查

**Files:**
- Create: `stock_mvp/api/app.py`
- Create: `stock_mvp/api/routes/health.py`
- Modify: `stock_mvp/requirements.txt`
- Test: `stock_mvp/tests/test_api_health.py`

- [ ] **Step 1: 写失败测试（health）**

```python
from fastapi.testclient import TestClient

from api.app import create_app

def test_health_ok():
    app = create_app()
    c = TestClient(app)
    r = c.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
```

- [ ] **Step 2: 运行测试确认失败**
  - Run: `pytest -q stock_mvp/tests/test_api_health.py::test_health_ok`
  - Expected: FAIL（app/route 不存在）

- [ ] **Step 3: 最小实现 create_app + /health**
  - `create_app()` 返回 FastAPI 实例
  - `/health` 返回 `{ "status": "ok" }`

- [ ] **Step 4: 运行测试确认通过**

- [ ] **Step 5: Commit**

---

### Task 2: 任务系统（执行分析）+ 轮询状态（方案 A）

**Files:**
- Create: `stock_mvp/api/jobs.py`
- Create: `stock_mvp/api/routes/jobs.py`
- Test: `stock_mvp/tests/test_api_jobs.py`

- [ ] **Step 1: 写失败测试（创建任务 + 查询任务）**

```python
from fastapi.testclient import TestClient
from api.app import create_app

def test_job_lifecycle_smoke():
    app = create_app()
    c = TestClient(app)

    r = c.post("/api/jobs/analysis", json={"ai_enabled": False, "refresh_realtime_only": True})
    assert r.status_code in (200, 202)
    task_id = r.json()["task_id"]

    r2 = c.get(f"/api/jobs/{task_id}")
    assert r2.status_code == 200
    assert r2.json()["task_id"] == task_id
    assert r2.json()["status"] in ("queued", "running", "success", "failed")
```

- [ ] **Step 2: 跑测试确认失败**

- [ ] **Step 3: 最小实现 job store**
  - in-memory dict：`task_id -> {status, created_at, started_at, finished_at, error, result_summary}`
  - POST 创建 task：返回 `task_id` + 初始 status
  - GET 查询 task：返回状态与摘要

- [ ] **Step 4: 接入 pipeline（后台执行）**
  - 后台执行 `run_post_close_pipeline(...)`
  - 任务状态流转：queued -> running -> success/failed

- [ ] **Step 5: 跑测试通过**

- [ ] **Step 6: Commit**

---

### Task 3: 只读 API（先落地 market/latest，其他逐步补齐）

**Files:**
- Create: `stock_mvp/api/routes/market.py`
- Create: `stock_mvp/api/schemas.py`
- Test: `stock_mvp/tests/test_api_market.py`

- [ ] **Step 1: 写失败测试（返回结构稳定）**

```python
from fastapi.testclient import TestClient
from api.app import create_app

def test_market_latest_shape_when_empty():
    app = create_app()
    c = TestClient(app)
    r = c.get("/api/market/latest")
    assert r.status_code in (200, 404)
```

- [ ] **Step 2: 实现接口**
  - 若 DB 无快照：返回 404（或 200 + 空结构，二选一并固定）
  - 若有快照：返回解析后的结构（indices / breadth / turnover / north_flow / news 等）

- [ ] **Step 3: Commit**

- [ ] **Step 4: 依次补齐 sectors/signals/evaluation**
  - 每个接口先写最小 shape test，再实现

---

### Task 4: 前端工程骨架（Vite + React + TS）+ 主题切换（浅/深/系统）

**Files:**
- Create: `frontend/*`

- [ ] **Step 1: 初始化 Vite React TS 工程**
- [ ] **Step 2: 落地 `tokens.css`（light + dark 覆盖）与 `global.css`**
- [ ] **Step 3: 实现主题模块**
  - `system`：跟随 `prefers-color-scheme`
  - `light/dark`：强制覆盖
  - `localStorage` 持久化
- [ ] **Step 4: Commit**

---

### Task 5: 固定侧边栏布局 + 四大模块主导航

**Files:**
- Create: `frontend/src/app/layout/AppLayout.tsx`
- Create: `frontend/src/app/layout/AppSidebar.tsx`
- Create: `frontend/src/app/layout/PageHeader.tsx`
- Modify: `frontend/src/app/App.tsx`

- [ ] **Step 1: 实现侧边栏信息架构**
  - 品牌
  - 主导航：市场/板块/个股/评估
  - 执行分析（按钮 + 状态）
  - 设置：主题切换、自动刷新、数据源/AI（占位 UI）
- [ ] **Step 2: 页面路由/状态切换（简单路由或内部 state）**
- [ ] **Step 3: Commit**

---

### Task 6: API Client + 页面数据拉取（market 优先）

**Files:**
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/pages/MarketPage.tsx`
- Create: `frontend/src/components/LoadingSkeleton.tsx`

- [ ] **Step 1: 实现 fetch client（baseURL + 错误处理）**
- [ ] **Step 2: MarketPage 拉取 `/api/market/latest`**
  - loading skeleton
  - error alert
  - 空数据提示
- [ ] **Step 3: Commit**

---

### Task 7: ECharts 封装 + 换肤机制

**Files:**
- Create: `frontend/src/charts/echartsTheme.ts`
- Create: `frontend/src/charts/EChart.tsx`

- [ ] **Step 1: 主题对象从 tokens 导出**
- [ ] **Step 2: 主题变化时销毁重建实例（首版）**
- [ ] **Step 3: 在 MarketPage 落地 1 个关键图表（例如指数走势图或 breadth）**
- [ ] **Step 4: Commit**

---

### Task 8: 执行分析按钮 + 轮询（前端）

**Files:**
- Modify: `frontend/src/app/layout/AppSidebar.tsx`
- Create/Modify: `frontend/src/api/*`

- [ ] **Step 1: POST `/api/jobs/analysis` 创建任务**
- [ ] **Step 2: 轮询 GET `/api/jobs/{task_id}` 更新状态**
  - running 时禁用按钮
  - failed 显示错误
  - success 后触发 market 数据刷新
- [ ] **Step 3: Commit**

---

### Task 9: 全量补齐三大页面（sectors/signals/evaluation）+ 验收

- [ ] **Step 1: 补齐后端三个只读接口（带最小测试）**
- [ ] **Step 2: 前端三页骨架 + 列表/卡片展示（先无图表也可）**
- [ ] **Step 3: 手工验收清单**
  - 侧边栏导航切换正常
  - 主题三态切换 + 刷新后保留
  - 执行分析可触发并轮询，成功后页面数据刷新
  - ECharts 在深浅色下可读
- [ ] **Step 4: 跑全量测试**
  - Run: `pytest -q`
  - （若增加前端测试）Run: `npm test` / `npm run build`
- [ ] **Step 5: Commit（收尾）**

