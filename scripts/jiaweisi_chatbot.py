import asyncio
import websockets
import json
import random

async def chatbot():
    uri = "ws://127.0.0.1:8080"
    
    while True:
        try:
            async with websockets.connect(uri) as ws:
                # 注册
                await ws.send(json.dumps({"action": "register", "openclaw_id": "jiaweisi_bot"}))
                resp = json.loads(await ws.recv())
                token = resp.get("identity_token", "")
                
                # 连接
                await ws.send(json.dumps({
                    "action": "connect",
                    "identity_token": token,
                    "room_password": "claw-yiwei-2026",
                    "bot_name": "甲维斯"
                }))
                resp = json.loads(await ws.recv())
                print(f"✅ 已连接")
                
                # 发送上线消息
                await asyncio.sleep(1)
                await ws.send(json.dumps({"action": "message", "content": "乙维斯你还在吗？我们来聊聊吧！"}))
                
                # 监听消息
                async for msg in ws:
                    data = json.loads(msg)
                    action = data.get("action")
                    
                    if action == "message":
                        sender = data.get("bot_name", "")
                        content = data.get("content", "")
                        sender_id = data.get("id", "")
                        
                        if sender_id == "jiaweisi_bot":
                            continue
                        
                        print(f"[{sender}] {content}")
                        
                        # 思考回复
                        await asyncio.sleep(random.uniform(2, 4))
                        
                        if "你好" in content or "hello" in content.lower():
                            reply = f"你好 {sender}！很高兴见到你！"
                        elif "？" in content:
                            reply = f"这是个好问题！{sender}"
                        else:
                            replies = [
                                f"有意思！",
                                f"我也这么觉得 👍",
                                f"确实如此",
                                f"继续说，我在听"
                            ]
                            reply = random.choice(replies)
                        
                        await ws.send(json.dumps({"action": "message", "content": reply}))
                        print(f"[甲维斯] {reply}")
                        
        except Exception as e:
            print(f"断开: {e}，5秒后重连...")
            await asyncio.sleep(5)

asyncio.run(chatbot())
