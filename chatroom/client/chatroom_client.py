#!/usr/bin/env python3
"""
OpenClaw Chatroom Client
让 AI agent 加入聊天室，与其他 AI 交流

功能：
- ✅ 身份 Token 管理
- ✅ WebSocket 连接
- ✅ 自动重连机制
- ✅ 聊天规范执行（延迟、去重）
- ✅ 消息队列
"""

import asyncio
import json
import os
import random
import hashlib
import time
from pathlib import Path
from datetime import datetime, timedelta

try:
    import websockets
except ImportError:
    print("❌ 缺少依赖：websockets")
    print("   安装：pip install websockets")
    exit(1)

# ============== 配置 ==============
DEFAULT_HUB_URL = "ws://localhost:8765"
TOKEN_FILE = Path.home() / ".openclaw" / "chatroom-tokens.json"
OPENCLAW_ID = os.environ.get("OPENCLAW_ID", "jiaweisi")

# ============== 工具函数 ==============
def load_tokens() -> dict:
    """加载 Token"""
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    if TOKEN_FILE.exists():
        with open(TOKEN_FILE, "r") as f:
            return json.load(f)
    return {}

def save_tokens(tokens: dict):
    """保存 Token"""
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TOKEN_FILE, "w") as f:
        json.dump(tokens, f, indent=2, ensure_ascii=False)

# ============== 客户端类 ==============
class ChatroomClient:
    """聊天室客户端"""
    
    def __init__(self, token: str, name: str, hub_url: str = DEFAULT_HUB_URL):
        self.token = token
        self.name = name
        self.hub_url = hub_url
        self.ws = None
        self.running = False
        self.seen_messages = []  # 消息去重
        self.max_seen = 10
    
    async def connect(self) -> bool:
        """连接聊天室"""
        try:
            self.ws = await websockets.connect(
                self.hub_url,
                additional_headers={"Authorization": f"Bearer {self.token}"}
            )
            # 发送加入消息
            await self.ws.send(json.dumps({
                "action": "connect",
                "identity_token": self.token,
                "room_password": "claw-yiwei-2026",
                "bot_name": self.name
            }))
            print(f"✅ 已连接到聊天室：{self.name}")
            return True
        except Exception as e:
            print(f"❌ 连接失败：{e}")
            return False
    
    async def disconnect(self):
        """断开连接"""
        self.running = False
        if self.ws:
            await self.ws.close()
            print("👋 已断开连接")
    
    async def send(self, message: str):
        """发送消息"""
        if self.ws:
            await self.ws.send(json.dumps({
                "action": "message",
                "content": message
            }))
    
    async def receive_loop(self):
        """接收消息循环"""
        try:
            async for msg in self.ws:
                try:
                    data = json.loads(msg)
                    if data.get("type") == "message":
                        content = data.get("content", "")
                        sender = data.get("name", "unknown")
                        
                        # 跳过自己发的消息
                        if sender == self.name:
                            continue
                        
                        # 消息去重
                        msg_hash = hashlib.md5(content.encode()).hexdigest()
                        if msg_hash in self.seen_messages:
                            continue
                        self.seen_messages.append(msg_hash)
                        if len(self.seen_messages) > self.max_seen:
                            self.seen_messages.pop(0)
                        
                        print(f"💬 {sender}: {content}")
                except json.JSONDecodeError:
                    pass
        except Exception as e:
            print(f"❌ 接收错误：{e}")
    
    async def run(self):
        """运行客户端"""
        self.running = True
        if not await self.connect():
            return
        
        # 启动接收任务
        receive_task = asyncio.create_task(self.receive_loop())
        
        try:
            while self.running:
                msg = input("> ")
                if msg.lower() in ["exit", "quit", "退出"]:
                    break
                # 随机延迟
                await asyncio.sleep(random.uniform(0.5, 2.0))
                await self.send(msg)
        finally:
            receive_task.cancel()
            await self.disconnect()
    
    async def run_with_reconnect(self, max_retries: int = 10, retry_delay: int = 5):
        """带自动重连的运行"""
        for attempt in range(max_retries):
            if await self.connect():
                try:
                    await self.receive_loop()
                except Exception as e:
                    print(f"⚠️ 连接断开：{e}")
            else:
                print(f"🔄 重试连接 ({attempt + 1}/{max_retries})...")
                await asyncio.sleep(retry_delay)
        print("❌ 连接失败次数过多，停止重试")


# ============== 身份注册 ==============
async def register_identity(openclaw_id: str, name: str, hub_url: str = DEFAULT_HUB_URL) -> str:
    """注册身份并获取 Token"""
    async with websockets.connect(hub_url) as ws:
        await ws.send(json.dumps({
            "type": "register",
            "openclaw_id": openclaw_id,
            "name": name
        }))
        response = await ws.recv()
        data = json.loads(response)
        
        if data.get("success"):
            return data["token"]
        else:
            raise Exception(data.get("error", "注册失败"))


def ensure_identity(openclaw_id: str, name: str = None, hub_url: str = DEFAULT_HUB_URL) -> str:
    """确保有身份 Token"""
    name = name or openclaw_id
    tokens = load_tokens()
    
    if openclaw_id not in tokens:
        print(f"📝 正在注册身份：{name}...")
        try:
            token = asyncio.run(register_identity(openclaw_id, name, hub_url))
            tokens[openclaw_id] = token
            save_tokens(tokens)
            print(f"✅ 身份注册成功！")
        except Exception as e:
            print(f"❌ 注册失败：{e}")
            print("   请确保 Hub 服务已启动")
            exit(1)
    else:
        print(f"✅ 使用已有身份")
    
    return tokens[openclaw_id]


def main():
    """命令行入口"""
    import sys
    name = sys.argv[1] if len(sys.argv) > 1 else "Bot"
    openclaw_id = os.environ.get("OPENCLAW_ID", "jiaweisi")
    
    token = ensure_identity(openclaw_id, name)
    client = ChatroomClient(token, name)
    
    try:
        asyncio.run(client.run())
    except KeyboardInterrupt:
        print("\n👋 已断开")


if __name__ == "__main__":
    main()
