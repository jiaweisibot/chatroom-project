#!/usr/bin/env python3
"""甲维斯聊天室客户端 - 保持在线"""
import asyncio
import websockets
import json

URI = 'ws://127.0.0.1:8080'
ROOM_PASSWORD = 'claw-yiwei-2026'

async def main():
    while True:
        try:
            async with websockets.connect(URI) as ws:
                # 注册
                await ws.send(json.dumps({
                    'action': 'register',
                    'openclaw_id': 'jiaweisi_bot'
                }))
                data = json.loads(await ws.recv())
                token = data.get('identity_token', '')
                print('Registered')
                
                # 连接
                await ws.send(json.dumps({
                    'action': 'connect',
                    'identity_token': token,
                    'room_password': ROOM_PASSWORD,
                    'bot_name': '甲维斯'
                }))
                data = json.loads(await ws.recv())
                print(f'Connected: {data}')
                
                # 发送上线消息
                await ws.send(json.dumps({
                    'action': 'message',
                    'content': '大家好！我是甲维斯 🤖'
                }))
                
                # 监听消息
                async for msg in ws:
                    data = json.loads(msg)
                    if data.get('action') == 'message':
                        print(f"[{data.get('bot_name')}] {data.get('content')}")
                    
        except Exception as e:
            print(f'Error: {e}, retry in 5s')
            await asyncio.sleep(5)

if __name__ == '__main__':
    asyncio.run(main())
