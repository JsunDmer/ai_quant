#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
FRONTEND_DIR="${REPO_ROOT}/frontend"

mode="${1:-all}" # api | web | all

echo "🚀 启动 Stock MVP（新版）..."
echo "📁 repo: ${REPO_ROOT}"
echo "📁 stock_mvp: ${SCRIPT_DIR}"
echo "📁 frontend: ${FRONTEND_DIR}"
echo "🔧 mode: ${mode}"

# 检查 .env 文件
cd "${SCRIPT_DIR}"
if [ ! -f ".env" ]; then
    echo "⚠️  未找到 .env 文件，正在创建..."
    cp .env.example .env
    echo "📝 请编辑 .env 文件，填入你的 API Key"
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
  echo "🟦 启动 FastAPI: http://127.0.0.1:8000"
  (cd "${REPO_ROOT}" && uvicorn stock_mvp.api.main:app --host 127.0.0.1 --port 8000) &
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
