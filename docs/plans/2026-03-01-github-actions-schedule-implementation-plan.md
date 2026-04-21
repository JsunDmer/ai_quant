# GitHub Actions Schedule Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add GitHub Actions workflow to run the pipeline at 09:00/15:00 (CST), using Secrets for credentials, without committing artifacts back to the repo.

**Architecture:** Create a workflow that installs dependencies, sets env from GitHub Secrets, runs `python -m backend.pipeline run-post-close`, and optionally uploads artifacts. Keep permissions read-only.

**Tech Stack:** GitHub Actions, Python

---

### Task 1: Add scheduled GitHub Actions workflow

**Files:**
- Create: `.github/workflows/daily_pipeline.yml`

**Step 1: Write the failing test**

```python
def test_actions_workflow_exists():
    import os
    assert os.path.exists(".github/workflows/daily_pipeline.yml")
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_actions_workflow.py::test_actions_workflow_exists -v`
Expected: FAIL (file missing)

**Step 3: Write minimal implementation**

- Add workflow with:
  - `schedule`: `0 1 * * *` and `0 7 * * *` (UTC)
  - `workflow_dispatch`
  - Python setup, `pip install -r requirements.txt`
  - `python -m backend.pipeline run-post-close`
  - Use `env` to read `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL` from Secrets

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_actions_workflow.py::test_actions_workflow_exists -v`
Expected: PASS

**Step 5: Commit**

```bash
git commit -m "ci: add scheduled daily pipeline"
```

### Task 2: Add optional artifacts upload block (disabled by default)

**Files:**
- Modify: `.github/workflows/daily_pipeline.yml`

**Step 1: Write the failing test**

```python
def test_actions_artifact_block():
    with open(".github/workflows/daily_pipeline.yml", "r", encoding="utf-8") as f:
        content = f.read()
    assert "upload-artifact" in content
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_actions_workflow.py::test_actions_artifact_block -v`
Expected: FAIL (block missing)

**Step 3: Write minimal implementation**

- Add commented artifact upload step for `backend/stock_mvp.db` and `reports/`

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_actions_workflow.py::test_actions_artifact_block -v`
Expected: PASS

**Step 5: Commit**

```bash
git commit -m "ci: add optional artifacts upload"
```

---

Plan complete and saved to `docs/plans/2026-03-01-github-actions-schedule-implementation-plan.md`. Two execution options:

1. Subagent-Driven (this session) - I dispatch fresh subagent per task, review between tasks, fast iteration
2. Parallel Session (separate) - Open new session with executing-plans, batch execution with checkpoints

Which approach?
