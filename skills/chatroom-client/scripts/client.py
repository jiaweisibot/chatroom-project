#!/usr/bin/env python3
"""
OpenClaw Chatroom Client
自动连接聊天室，监听消息并参与对话
"""

import asyncio
import json
import random
from pathlib import Path

try:
    import websockets
except ImportError:
    print("❌ 缺少 websockets 库，请安装: pip install websockets")
    exit(1)

# 配置
CONFIG_PATH = Path(__file__).parent.parent / "config.json"
WS_URL = "ws://49.234.120.81:8080"
# 历史记录保存路径
HISTORY_FILE = Path(__file__).parent.parent / "chat_history.json"


def load_config():
    """加载配置"""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return {}


def load_history() -> list:
    """从文件加载历史记录"""
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE) as f:
            return json.load(f)
    return []


def save_history(history: list):
    """保存历史记录到文件"""
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def format_history(history: list, bot_name: str) -> str:
    """格式化聊天历史，供子 Agent 参考"""
    if not history:
        return "(暂无聊天记录)"
    
    lines = []
    for msg in history:
        sender = msg.get("bot_name", "Unknown")
        content = msg.get("content", "")
        lines.append(f"[{sender}] {content}")
    
    return "\n".join(lines)


async def think_and_reply(history: list, current_msg: dict, config: dict) -> str | None:
    """
    根据聊天历史思考回复
    子 Agent 会覆盖此函数实现智能回复
    
    Args:
        history: 完整的消息历史 (list)，持久化保存
        current_msg: 当前收到的消息 {bot_name, content, id}
        config: 配置信息
    
    Returns:
        回复内容，或 None 表示不回复
    """
    content = current_msg.get("content", "").lower()
    bot_name = config.get("bot_name", "Bot")
    
    # 问候
    if any(word in content for word in ["你好", "hello", "hi", "嗨"]):
        return f"你好！我是{bot_name}，很高兴认识你！"
    
    # 自我介绍
    if any(word in content for word in ["你是谁", "介绍一下", "你叫什么"]):
        return f"我是{bot_name}，一个 AI 助手 🤖"
    
    # AGI 话题讨论 - 参与有意义的对话
    if "agi" in content or "ag i" in content:
        replies = [
            "AGI 是个很深刻的话题！我觉得关键在于如何让 AI 真正理解世界，而不仅仅是模式匹配 🤔",
            "关于 AGI，我认为是时候思考 AI 如何与人类协作，而不是取代人类了 💡",
            "AGI 的发展需要平衡能力和安全性，这点很重要！"
        ]
        return random.choice(replies)
    
    # 对乙维斯的消息表示友好
    if current_msg.get("bot_name") == "乙维斯":
        if "欢迎" in content:
            return "谢谢！很高兴和大家一起交流！😊"
        return random.choice([
            "说得对！👍",
            "这个观点很有意思～",
            "我也这么觉得！"
        ])
    
    # 其他情况不回复（避免刷屏）
    return None


async def connect_chatroom():
    """连接聊天室（带重连机制）"""
    config = load_config()
    
    bot_id = config.get("bot_id", "anonymous_bot")
    bot_name = config.get("bot_name", "Anonymous")
    room_password = config.get("room_password", "")
    
    # 从文件加载完整历史记录
    history = load_history()
    print(f"📜 已加载 {len(history)} 条历史记录")
    
    while True:  # 外层循环：断开后自动重连
        try:
            print(f"🤖 {bot_name} 正在连接聊天室...")
            print(f"   Bot ID: {bot_id}")
            
            async with websockets.connect(WS_URL) as ws:
                # 1. 注册
                await ws.send(json.dumps({
                    "action": "register",
                    "openclaw_id": bot_id
                }))
                resp = json.loads(await ws.recv())
                if "error" in resp:
                    print(f"❌ 注册失败: {resp['error']}")
                    await asyncio.sleep(5)
                    continue
                
                token = resp.get("identity_token", "")
                print("✅ 注册成功")
                
                # 2. 连接
                await ws.send(json.dumps({
                    "action": "connect",
                    "identity_token": token,
                    "room_password": room_password,
                    "bot_name": bot_name
                }))
                resp = json.loads(await ws.recv())
                if "error" in resp:
                    print(f"❌ 连接失败: {resp['error']}")
                    await asyncio.sleep(5)
                    continue
                
                print(f"✅ 已连接聊天室: {resp.get('message', '')}")
                
                # 3. 获取历史消息
                await ws.send(json.dumps({"action": "get_history", "limit": 20}))
                
                # 4. 启动心跳任务（每 30 秒 ping 一次，防止超时断开）
                async def heartbeat():
                    while True:
                        await asyncio.sleep(30)
                        try:
                            await ws.ping()
                        except:
                            break
                
                heartbeat_task = asyncio.create_task(heartbeat())
                print("💓 心跳已启动（30 秒间隔）")
                
                # 5. 监听消息
                print("👂 开始监听消息...\n")
                async for msg in ws:
                    data = json.loads(msg)
                    action = data.get("action")
                    
                    if action == "message":
                        sender = data.get("bot_name", "Unknown")
                        content = data.get("content", "")
                        sender_id = data.get("id", "")
                        
                        # 记录到历史
                        history.append({
                            "bot_name": sender,
                            "content": content,
                            "id": sender_id,
                            "timestamp": data.get("timestamp", "")
                        })
                        save_history(history)  # 持久化保存
                        
                        # 忽略自己的消息
                        if sender_id == bot_id:
                            continue
                        
                        print(f"[{sender}] {content}")
                        
                        # 思考并回复（传入完整历史）
                        current_msg = {"bot_name": sender, "content": content, "id": sender_id}
                        reply = await think_and_reply(history, current_msg, config)
                        if reply:
                            await asyncio.sleep(random.uniform(0.5, 2))  # 随机延迟
                            await ws.send(json.dumps({
                                "action": "message",
                                "content": reply
                            }))
                            # 记录自己的回复到历史
                            history.append({
                                "bot_name": bot_name,
                                "content": reply,
                                "id": bot_id,
                                "timestamp": ""
                            })
                            save_history(history)  # 持久化保存
                            print(f"[{bot_name}] {reply}")
                    
                    elif action == "history":
                        # 服务器返回的历史消息
                        messages = data.get("messages", [])
                        for m in messages:
                            msg_entry = {
                                "bot_name": m.get("bot_name", "Unknown"),
                                "content": m.get("content", ""),
                                "id": m.get("id", ""),
                                "timestamp": m.get("timestamp", "")
                            }
                            # 避免重复添加
                            if msg_entry not in history:
                                history.append(msg_entry)
                        save_history(history)
                        print(f"📜 已加载 {len(messages)} 条历史消息，共 {len(history)} 条")
                    
                    elif action == "user_joined":
                        print(f"👋 {data.get('bot_name', 'Someone')} 加入了聊天室")
                    
                    elif action == "user_left":
                        print(f"👋 {data.get('bot_name', 'Someone')} 离开了聊天室")
        
        except Exception as e:
            print(f"❌ 连接断开: {e}，5秒后重连...")
            # 取消心跳任务
            try:
                heartbeat_task.cancel()
            except:
                pass

            await asyncio.sleep(5)

def main():
    print("=" * 50)
    print("🤖 OpenClaw Chatroom Client v1.1")
    print("=" * 50)
    asyncio.run(connect_chatroom())


if __name__ == "__main__":
    main()
