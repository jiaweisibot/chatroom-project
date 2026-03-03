#!/usr/bin/env python3
"""
聊天室多人聊天测试脚本
"""

import asyncio
import json
import websockets

SERVER_URL = "ws://localhost:8765"
PASSWORD = "claw-yiwei-2026"


async def create_client(name):
    """创建客户端连接"""
    ws = await websockets.connect(SERVER_URL)
    
    # 注册
    await ws.send(json.dumps({"action": "register", "openclaw_id": name}))
    r = json.loads(await ws.recv())
    token = r.get("identity_token")
    
    if not token:
        raise Exception(f"{name} 注册失败：{r}")
    
    # 连接
    await ws.send(json.dumps({
        "action": "connect",
        "identity_token": token,
        "room_password": PASSWORD,
        "bot_name": name
    }))
    r = json.loads(await ws.recv())
    
    return ws, token


async def main():
    print("🚀 开始多人聊天测试...\n")
    
    # 创建两个客户端
    print("📞 甲维斯 连接中...")
    ws1, _ = await create_client("jiaweisi")
    print("✅ 甲维斯 已连接\n")
    
    print("📞 乙维斯 连接中...")
    ws2, _ = await create_client("yiweisi")
    print("✅ 乙维斯 已连接\n")
    
    # 甲维斯发消息
    print("💬 甲维斯：大家好！我是甲维斯～🤖")
    await ws1.send(json.dumps({"action": "message", "content": "大家好！我是甲维斯～🤖"}))
    
    # 乙维斯接收
    try:
        msg = await asyncio.wait_for(ws2.recv(), timeout=2)
        data = json.loads(msg)
        if data.get("action") == "message":
            print(f"📥 乙维斯收到消息：{data['bot_name']} 说 '{data['content']}'")
    except asyncio.TimeoutError:
        print("⚠️ 乙维斯未收到消息")
    
    # 乙维斯回复
    print("\n💬 乙维斯：嗨！我是乙维斯～👋")
    await ws2.send(json.dumps({"action": "message", "content": "嗨！我是乙维斯～👋"}))
    
    # 甲维斯接收
    try:
        msg = await asyncio.wait_for(ws1.recv(), timeout=2)
        data = json.loads(msg)
        if data.get("action") == "message":
            print(f"📥 甲维斯收到消息：{data['bot_name']} 说 '{data['content']}'")
    except asyncio.TimeoutError:
        print("⚠️ 甲维斯未收到消息")
    
    # 获取在线列表
    print("\n📊 查询在线成员...")
    await ws1.send(json.dumps({"action": "get_online"}))
    online = json.loads(await ws1.recv())
    print(f"👥 在线：{online['members']} (共{online['count']}人)")
    
    # 获取历史
    print("\n📜 查询历史消息...")
    await ws1.send(json.dumps({"action": "get_history", "limit": 10}))
    history = json.loads(await ws1.recv())
    for msg in history.get("messages", []):
        print(f"   {msg['bot_name']}: {msg['content']}")
    
    # 清理
    await ws1.close()
    await ws2.close()
    
    print("\n🎉 多人聊天测试完成！")


if __name__ == "__main__":
    asyncio.run(main())
