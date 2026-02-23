#!/bin/bash

echo "🚀 启动 Stock MVP..."

# 检查 .env 文件
if [ ! -f ".env" ]; then
    echo "⚠️  未找到 .env 文件，正在创建..."
    cp .env.example .env
    echo "📝 请编辑 .env 文件，填入你的 API Key"
    exit 1
fi

# 检查虚拟环境
if [ ! -d ".venv" ]; then
    echo "📦 创建虚拟环境..."
    python3 -m venv .venv
fi

# 激活虚拟环境
source .venv/bin/activate

# 安装依赖
echo "📥 安装依赖..."
pip install -r requirements.txt -q

# 启动应用
echo "🌟 启动 Streamlit 应用..."
streamlit run app.py
