# GitHub Actions 定时运行设计

## 目标
- 使用 GitHub Actions 在 09:00 与 15:00（北京时间）自动执行流水线。
- 不在代码中写任何明文密钥，全部通过 GitHub Secrets 注入。
- 产物不提交回仓库，必要时仅通过 logs 或 artifacts 获取。

## 触发与执行
- 新增 `.github/workflows/daily_pipeline.yml`。
- 定时触发：UTC `01:00` 与 `07:00`（对应北京时间 09:00/15:00）。
- 手动触发：`workflow_dispatch`。
- 执行入口：`python -m pipeline run-post-close`。

## Secrets 与权限
- Secrets：`LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL`。
- 权限：仅需 `contents: read`（不写回仓库）。

## 产物策略
- 默认仅保留 Actions 日志。
- 可选 artifacts：`stock_mvp/stock_mvp.db` 与 `reports/`（如需要再启用）。

## 失败处理
- 失败时保留完整日志输出，供排查。
- 不中断后续定时触发。
