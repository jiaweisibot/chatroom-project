#!/bin/bash
# 启动 OpenClaw 聊天室 Hub 服务

echo "🚀 启动 OpenClaw 聊天室 Hub..."
echo ""

# 进入项目目录
cd "$(dirname "$0")"

# 检查依赖
python3 -c "import websockets" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  安装依赖：websockets"
    pip3 install websockets -q
fi

# 启动服务
echo "📍 服务地址：ws://localhost:8765"
echo "💡 按 Ctrl+C 停止服务"
echo ""

python3 -m chatroom.server.hub
