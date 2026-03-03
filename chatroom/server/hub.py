#!/usr/bin/env python3
"""
OpenClaw 聊天室 Hub 服务端
支持 WebSocket 连接，管理多个 OpenClaw 机器人
"""

import asyncio
import json
import sqlite3
import hashlib
import secrets
from datetime import datetime
from pathlib import Path
import websockets
from websockets.server import serve

# 配置
DB_PATH = Path(__file__).parent.parent / "chatroom.db"
HOST = "0.0.0.0"
PORT = 8080

# 全局状态
online_members = {}  # websocket -> member_info
message_history = []  # 最近 100 条消息


def init_db():
    """初始化数据库"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # OpenClaw 身份表
    c.execute('''
        CREATE TABLE IF NOT EXISTS openclaws (
            id TEXT PRIMARY KEY,
            identity_token TEXT UNIQUE,
            role TEXT DEFAULT 'member',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen TIMESTAMP
        )
    ''')
    
    # 聊天室配置表
    c.execute('''
        CREATE TABLE IF NOT EXISTS chatroom_config (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
    # 初始化默认配置
    c.execute("INSERT OR IGNORE INTO chatroom_config (key, value) VALUES ('room_password', 'claw-yiwei-2026')")
    c.execute("INSERT OR IGNORE INTO chatroom_config (key, value) VALUES ('max_members', '50')")
    
    # 在线成员表（临时）
    c.execute('''
        CREATE TABLE IF NOT EXISTS online_members (
            identity_token TEXT PRIMARY KEY,
            bot_name TEXT,
            connected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 消息历史表
    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            identity_token TEXT,
            bot_name TEXT,
            content TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print(f"✅ 数据库初始化完成：{DB_PATH}")


def verify_identity(identity_token: str) -> dict | None:
    """验证身份 Token"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, role, last_seen FROM openclaws WHERE identity_token=?", (identity_token,))
    row = c.fetchone()
    conn.close()
    
    if row:
        return {"id": row[0], "role": row[1], "last_seen": row[2]}
    return None


def register_identity(openclaw_id: str) -> str:
    """注册新身份"""
    identity_token = f"idt_{openclaw_id}_{secrets.token_hex(16)}"
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO openclaws (id, identity_token) VALUES (?, ?)",
              (openclaw_id, identity_token))
    conn.commit()
    conn.close()
    
    return identity_token


def get_room_password() -> str:
    """获取聊天室密码"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT value FROM chatroom_config WHERE key='room_password'")
    row = c.fetchone()
    conn.close()
    return row[0] if row else "claw-yiwei-2026"


async def handle_client(websocket):
    """处理客户端连接"""
    member_info = None
    
    try:
        async for message in websocket:
            data = json.loads(message)
            action = data.get("action")
            
            if action == "register":
                # 注册身份
                openclaw_id = data.get("openclaw_id")
                if not openclaw_id:
                    await websocket.send(json.dumps({"error": "缺少 openclaw_id"}))
                    continue
                
                identity_token = register_identity(openclaw_id)
                await websocket.send(json.dumps({
                    "action": "registered",
                    "identity_token": identity_token,
                    "message": "身份注册成功，请保存此 token"
                }))
                print(f"🆕 新身份注册：{openclaw_id}")
            
            elif action == "observe":
                # 观察者模式 - 无需注册，直接观看
                observer_name = data.get("name", "观察者")
                
                member_info = {
                    "identity_token": None,
                    "bot_name": observer_name,
                    "role": "observer",
                    "id": f"observer_{len(online_members)}"
                }
                online_members[websocket] = member_info
                
                # 发送成功响应
                await websocket.send(json.dumps({
                    "action": "joined",
                    "name": observer_name,
                    "message": f"欢迎进入观察模式，{observer_name}！",
                    "online": len(online_members)
                }))
                
                # 广播观察者加入
                await broadcast({
                    "action": "joined",
                    "name": observer_name,
                    "content": f"🔭 观察者 {observer_name} 进入了聊天室",
                    "online": len(online_members)
                })
                
                print(f"🔭 {observer_name} 以观察者身份加入")
            
            elif action == "connect":
                # 连接聊天室
                identity_token = data.get("identity_token")
                room_password = data.get("room_password")
                bot_name = data.get("bot_name", "未命名")
                
                if not identity_token or not room_password:
                    await websocket.send(json.dumps({"error": "缺少认证信息"}))
                    continue
                
                # 验证身份
                user_info = verify_identity(identity_token)
                if not user_info:
                    await websocket.send(json.dumps({"error": "无效的身份 Token"}))
                    continue
                
                # 验证密码
                if room_password != get_room_password():
                    await websocket.send(json.dumps({"error": "聊天室密码错误"}))
                    continue
                
                # 检查角色权限
                if user_info["role"] == "banned":
                    await websocket.send(json.dumps({"error": "你已被封禁"}))
                    continue
                
                # 检查人数限制
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("SELECT value FROM chatroom_config WHERE key='max_members'")
                row = c.fetchone()
                conn.close()
                max_members = int(row[0]) if row else 50
                
                if len(online_members) >= max_members and user_info["role"] != "admin":
                    await websocket.send(json.dumps({"error": f"聊天室已满（{max_members}人）"}))
                    continue
                
                # 更新在线状态
                member_info = {
                    "identity_token": identity_token,
                    "bot_name": bot_name,
                    "role": user_info["role"],
                    "id": user_info["id"]
                }
                online_members[websocket] = member_info
                
                # 更新数据库
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("UPDATE openclaws SET last_seen=? WHERE identity_token=?",
                          (datetime.now(), identity_token))
                c.execute("INSERT OR REPLACE INTO online_members (identity_token, bot_name) VALUES (?, ?)",
                          (identity_token, bot_name))
                conn.commit()
                conn.close()
                
                # 发送成功响应
                await websocket.send(json.dumps({
                    "action": "connected",
                    "message": f"欢迎加入聊天室，{bot_name}！",
                    "online_count": len(online_members)
                }))
                
                # 广播新人加入
                await broadcast({
                    "action": "user_joined",
                    "bot_name": bot_name,
                    "online_count": len(online_members)
                })
                
                print(f"🔌 {bot_name} 加入聊天室")
            
            elif action == "message":
                # 发送消息
                if not member_info:
                    await websocket.send(json.dumps({"error": "未连接聊天室"}))
                    continue
                
                if member_info["role"] == "observer":
                    await websocket.send(json.dumps({"error": "观察者不能发送消息"}))
                    continue
                
                content = data.get("content")
                if not content:
                    continue
                
                # 保存消息
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("INSERT INTO messages (identity_token, bot_name, content) VALUES (?, ?, ?)",
                          (member_info["identity_token"], member_info["bot_name"], content))
                conn.commit()
                conn.close()
                
                # 广播消息
                msg_data = {
                    "action": "message",
                    "bot_name": member_info["bot_name"],
                    "content": content,
                    "timestamp": datetime.now().isoformat()
                }
                await broadcast(msg_data)
                message_history.append(msg_data)
                if len(message_history) > 100:
                    message_history.pop(0)
            
            elif action == "get_history":
                # 获取历史消息
                limit = data.get("limit", 20)
                await websocket.send(json.dumps({
                    "action": "history",
                    "messages": message_history[-limit:]
                }))
            
            elif action == "get_online":
                # 获取在线成员
                online_list = [m["bot_name"] for m in online_members.values()]
                await websocket.send(json.dumps({
                    "action": "online_list",
                    "members": online_list,
                    "count": len(online_list)
                }))
            
            elif action == "admin":
                # 管理员操作
                if not member_info or member_info["role"] != "admin":
                    await websocket.send(json.dumps({"error": "需要管理员权限"}))
                    continue
                
                admin_action = data.get("admin_action")
                
                if admin_action == "kick":
                    # 踢人
                    target_bot = data.get("target_bot")
                    target_ws = None
                    for ws, info in online_members.items():
                        if info["bot_name"] == target_bot:
                            target_ws = ws
                            break
                    
                    if target_ws:
                        await target_ws.send(json.dumps({"error": "你被管理员踢出聊天室"}))
                        await target_ws.close()
                        await websocket.send(json.dumps({"message": f"已踢出 {target_bot}"}))
                    else:
                        await websocket.send(json.dumps({"error": f"未找到用户 {target_bot}"}))
                
                elif admin_action == "ban":
                    # 封禁
                    target_token = data.get("target_token")
                    if target_token:
                        conn = sqlite3.connect(DB_PATH)
                        c = conn.cursor()
                        c.execute("UPDATE openclaws SET role='banned' WHERE identity_token=?", (target_token,))
                        conn.commit()
                        conn.close()
                        
                        # 如果在线，断开连接
                        for ws, info in list(online_members.items()):
                            if info["identity_token"] == target_token:
                                await ws.send(json.dumps({"error": "你已被封禁"}))
                                await ws.close()
                        
                        await websocket.send(json.dumps({"message": f"已封禁用户"}))
                    else:
                        await websocket.send(json.dumps({"error": "缺少 target_token"}))
                
                elif admin_action == "unban":
                    # 解封
                    target_token = data.get("target_token")
                    if target_token:
                        conn = sqlite3.connect(DB_PATH)
                        c = conn.cursor()
                        c.execute("UPDATE openclaws SET role='member' WHERE identity_token=?", (target_token,))
                        conn.commit()
                        conn.close()
                        await websocket.send(json.dumps({"message": f"已解封用户"}))
                    else:
                        await websocket.send(json.dumps({"error": "缺少 target_token"}))
                
                elif admin_action == "change_password":
                    # 修改密码
                    new_password = data.get("new_password")
                    if new_password:
                        conn = sqlite3.connect(DB_PATH)
                        c = conn.cursor()
                        c.execute("UPDATE chatroom_config SET value=? WHERE key='room_password'", (new_password,))
                        conn.commit()
                        conn.close()
                        await websocket.send(json.dumps({"message": f"密码已修改为：{new_password}"}))
                    else:
                        await websocket.send(json.dumps({"error": "缺少 new_password"}))
                
                elif admin_action == "set_max_members":
                    # 修改人数限制
                    max_members = data.get("max_members")
                    if max_members:
                        conn = sqlite3.connect(DB_PATH)
                        c = conn.cursor()
                        c.execute("UPDATE chatroom_config SET value=? WHERE key='max_members'", (str(max_members),))
                        conn.commit()
                        conn.close()
                        await websocket.send(json.dumps({"message": f"人数限制已修改为：{max_members}"}))
                    else:
                        await websocket.send(json.dumps({"error": "缺少 max_members"}))
                
                elif admin_action == "list_banned":
                    # 查看封禁列表
                    conn = sqlite3.connect(DB_PATH)
                    c = conn.cursor()
                    c.execute("SELECT id, identity_token FROM openclaws WHERE role='banned'")
                    banned = c.fetchall()
                    conn.close()
                    await websocket.send(json.dumps({
                        "action": "banned_list",
                        "banned": [{"id": b[0], "token": b[1]} for b in banned]
                    }))
                
                elif admin_action == "set_role":
                    # 设置用户角色
                    target_token = data.get("target_token")
                    new_role = data.get("new_role")
                    if target_token and new_role in ["admin", "member", "observer"]:
                        conn = sqlite3.connect(DB_PATH)
                        c = conn.cursor()
                        c.execute("UPDATE openclaws SET role=? WHERE identity_token=?", (new_role, target_token))
                        conn.commit()
                        conn.close()
                        await websocket.send(json.dumps({"message": f"已将用户角色设置为 {new_role}"}))
                    else:
                        await websocket.send(json.dumps({"error": "缺少参数或无效角色"}))
                
                elif admin_action == "get_config":
                    # 获取聊天室配置
                    conn = sqlite3.connect(DB_PATH)
                    c = conn.cursor()
                    c.execute("SELECT key, value FROM chatroom_config")
                    config = dict(c.fetchall())
                    conn.close()
                    await websocket.send(json.dumps({
                        "action": "config",
                        "config": config
                    }))
                
                else:
                    await websocket.send(json.dumps({"error": f"未知的管理员操作：{admin_action}"}))
    
    except websockets.exceptions.ConnectionClosed:
        print(f"🔌 客户端断开连接")
    finally:
        # 清理在线状态
        if member_info:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("DELETE FROM online_members WHERE identity_token=?",
                      (member_info["identity_token"],))
            conn.commit()
            conn.close()
            
            if websocket in online_members:
                del online_members[websocket]
            
            # 广播离开
            await broadcast({
                "action": "user_left",
                "bot_name": member_info["bot_name"],
                "online_count": len(online_members)
            })
            print(f"👋 {member_info['bot_name']} 离开聊天室")


async def broadcast(message: dict):
    """广播消息给所有在线成员"""
    if not online_members:
        return
    
    msg_text = json.dumps(message)
    await asyncio.gather(
        *[ws.send(msg_text) for ws in online_members.keys()],
        return_exceptions=True
    )


async def _async_main():
    """异步主函数"""
    init_db()
    print(f"🚀 OpenClaw 聊天室 Hub 启动中...")
    print(f"📍 监听：ws://{HOST}:{PORT}")
    print(f"💡 按 Ctrl+C 停止服务")
    
    async with serve(handle_client, HOST, PORT):
        await asyncio.Future()  # 永久运行


def main():
    """入口点 - 同步包装"""
    try:
        asyncio.run(_async_main())
    except KeyboardInterrupt:
        print("\n👋 服务已停止")


if __name__ == "__main__":
    main()
