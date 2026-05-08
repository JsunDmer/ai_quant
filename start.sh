#!/bin/bash

set -euo pipefail

# 脚本位于仓库根目录：SCRIPT_DIR == REPO_ROOT
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${SCRIPT_DIR}"
BACKEND_DIR="${REPO_ROOT}/backend"
FRONTEND_DIR="${REPO_ROOT}/frontend"

mode="${1:-all}" # api | web | all

echo "🚀 启动 Stock MVP（新版）..."
echo "📁 repo: ${REPO_ROOT}"
echo "📁 backend: ${BACKEND_DIR}"
echo "📁 frontend: ${FRONTEND_DIR}"
echo "🔧 mode: ${mode}"

# 检查后端 .env（与 backend/config 的 load_dotenv 工作目录一致）
cd "${BACKEND_DIR}"
if [ ! -f ".env" ]; then
    echo "⚠️  未找到 ${BACKEND_DIR}/.env，正在创建..."
    cp .env.example .env
    echo "📝 请编辑 ${BACKEND_DIR}/.env，填入你的 API Key"
    exit 1
fi

cleanup() {
  if [[ -n "${API_PID:-}" ]]; then
    kill "${API_PID}" >/dev/null 2>&1 || true
  fi
  if [[ -n "${WEB_PID:-}" ]]; then
    kill "${WEB_PID}" >/dev/null 2>&1 || true
  fi
  if [[ -n "${STREAMLIT_PID:-}" ]]; then
    kill "${STREAMLIT_PID}" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT INT TERM

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || { echo "❌ 缺少命令：$1"; exit 2; }
}

start_api() {
  need_cmd python
  need_cmd uvicorn
  echo "🟦 启动 FastAPI: http://127.0.0.1:8010"
  # 在 backend 目录下启动，保证 load_dotenv() 能读到 backend/.env；PYTHONPATH 指向仓库根以解析 backend 包
  (cd "${BACKEND_DIR}" && PYTHONPATH="${REPO_ROOT}" uvicorn backend.api.main:app --host 127.0.0.1 --port 8010) &
  API_PID=$!
}

start_web() {
  need_cmd npm
  if [[ ! -d "${FRONTEND_DIR}" ]]; then
    echo "❌ 未找到 frontend 目录：${FRONTEND_DIR}"
    exit 2
  fi
  echo "🟩 启动前端 Vite: http://127.0.0.1:5174"
  (cd "${FRONTEND_DIR}" && npm run dev -- --host 127.0.0.1 --port 5174) &
  WEB_PID=$!
}

case "${mode}" in
  api)
    start_api
    ;;
  web)
    start_web
    ;;
  all)
    start_api
    start_web
    ;;
  *)
    echo "用法：./start.sh [api|web|all]"
    exit 2
    ;;
esac

echo "✅ 已启动。按 Ctrl+C 退出并自动清理进程。"
wait
