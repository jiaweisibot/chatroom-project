#!/usr/bin/env python3
"""
聊天室功能测试脚本
测试：自动重连、消息去重、延迟规范
"""

import asyncio
import json
import websockets
import time

SERVER_URL = "ws://localhost:8765"
ROOM_PASSWORD = "claw-yiwei-2026"


async def test_duplicate_detection():
    """测试消息去重功能"""
    print("\n" + "="*60)
    print("🧪 测试 1：消息去重功能")
    print("="*60 + "\n")
    
    ws = await websockets.connect(SERVER_URL)
    
    # 注册
    await ws.send(json.dumps({
        "action": "register",
        "openclaw_id": "test_dup"
    }))
    response = json.loads(await ws.recv())
    token = response['identity_token']
    
    # 连接
    await ws.send(json.dumps({
        "action": "connect",
        "identity_token": token,
        "room_password": ROOM_PASSWORD,
        "bot_name": "去重测试"
    }))
    await ws.recv()
    
    # 发送相同消息两次
    test_message = "这是一条测试消息"
    
    print(f"📤 发送消息 1: {test_message}")
    await ws.send(json.dumps({
        "action": "message",
        "bot_name": "去重测试",
        "content": test_message
    }))
    await asyncio.sleep(0.5)
    
    print(f"📤 发送消息 2（重复）: {test_message}")
    await ws.send(json.dumps({
        "action": "message",
        "bot_name": "去重测试",
        "content": test_message
    }))
    await asyncio.sleep(0.5)
    
    # 发送不同消息
    different_message = "这是另一条消息"
    print(f"📤 发送消息 3（不同）: {different_message}")
    await ws.send(json.dumps({
        "action": "message",
        "bot_name": "去重测试",
        "content": different_message
    }))
    await asyncio.sleep(0.5)
    
    await ws.close()
    
    print("\n✅ 去重测试完成（检查服务端日志确认去重效果）")


async def test_connection_stability():
    """测试连接稳定性"""
    print("\n" + "="*60)
    print("🧪 测试 2：连接稳定性")
    print("="*60 + "\n")
    
    for i in range(3):
        print(f"📡 连接 {i+1}/3...")
        
        try:
            ws = await websockets.connect(SERVER_URL)
            
            # 注册
            await ws.send(json.dumps({
                "action": "register",
                "openclaw_id": f"test_stable_{i}"
            }))
            response = json.loads(await ws.recv())
            token = response['identity_token']
            
            # 连接
            await ws.send(json.dumps({
                "action": "connect",
                "identity_token": token,
                "room_password": ROOM_PASSWORD,
                "bot_name": f"稳定测试{i}"
            }))
            response = json.loads(await ws.recv())
            
            if "error" in response:
                print(f"   ❌ {response['error']}")
            else:
                print(f"   ✅ 连接成功，在线：{response.get('online_count', '?')}")
            
            await ws.close()
            
        except Exception as e:
            print(f"   ❌ 失败：{e}")
        
        await asyncio.sleep(1)
    
    print("\n✅ 稳定性测试完成")


async def test_message_broadcast():
    """测试消息广播"""
    print("\n" + "="*60)
    print("🧪 测试 3：消息广播（多客户端）")
    print("="*60 + "\n")
    
    # 创建两个连接
    ws1 = await websockets.connect(SERVER_URL)
    ws2 = await websockets.connect(SERVER_URL)
    
    # 注册
    await ws1.send(json.dumps({"action": "register", "openclaw_id": "broadcaster"}))
    await ws2.send(json.dumps({"action": "register", "openclaw_id": "receiver"}))
    
    token1 = json.loads(await ws1.recv())['identity_token']
    token2 = json.loads(await ws2.recv())['identity_token']
    
    # 连接
    await ws1.send(json.dumps({
        "action": "connect",
        "identity_token": token1,
        "room_password": ROOM_PASSWORD,
        "bot_name": "广播者"
    }))
    await ws1.recv()
    
    await ws2.send(json.dumps({
        "action": "connect",
        "identity_token": token2,
        "room_password": ROOM_PASSWORD,
        "bot_name": "接收者"
    }))
    await ws2.recv()
    
    print("📡 两个客户端已连接")
    await asyncio.sleep(1)
    
    # 广播者发送消息
    print("📤 广播者发送消息...")
    await ws1.send(json.dumps({
        "action": "message",
        "bot_name": "广播者",
        "content": "Hello, 这是广播测试！"
    }))
    
    # 接收者应该收到消息
    try:
        response = await asyncio.wait_for(ws2.recv(), timeout=2.0)
        data = json.loads(response)
        if data.get('action') == 'message':
            print(f"✅ 接收者收到：{data.get('bot_name')}: {data.get('content')}")
        else:
            print(f"⚠️  收到其他消息：{data}")
    except asyncio.TimeoutError:
        print("❌ 接收者未收到消息")
    
    await ws1.close()
    await ws2.close()
    
    print("\n✅ 广播测试完成")


async def main():
    """运行所有测试"""
    print("\n🚀 聊天室功能测试套件")
    print("="*60)
    
    try:
        await test_duplicate_detection()
        await asyncio.sleep(1)
        
        await test_connection_stability()
        await asyncio.sleep(1)
        
        await test_message_broadcast()
        
        print("\n" + "="*60)
        print("✅ 所有测试完成！")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n❌ 测试中断：{e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
