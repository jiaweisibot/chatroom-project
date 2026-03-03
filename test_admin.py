#!/usr/bin/env python3
"""
聊天室管理功能测试脚本
"""

import asyncio
import json
import websockets

SERVER_URL = "ws://localhost:8765"
PASSWORD = "claw-yiwei-2026"


async def register_only(name):
    """仅注册，不连接"""
    ws = await websockets.connect(SERVER_URL)
    await ws.send(json.dumps({"action": "register", "openclaw_id": name}))
    r = json.loads(await ws.recv())
    await ws.close()
    return r.get("identity_token")


async def connect(token, bot_name):
    """使用已有 token 连接"""
    ws = await websockets.connect(SERVER_URL)
    await ws.send(json.dumps({
        "action": "connect",
        "identity_token": token,
        "room_password": PASSWORD,
        "bot_name": bot_name
    }))
    r = json.loads(await ws.recv())
    return ws, r


async def test_admin_features():
    print("🚀 开始管理功能测试...\n")
    
    # 注册管理员
    print("📝 注册管理员...")
    admin_token = await register_only("admin_user")
    print(f"✅ 管理员 token: {admin_token[:30]}...")
    
    # 设置管理员角色（需要先用普通身份连接）
    print("\n🔧 设置管理员角色...")
    ws_temp, _ = await connect(admin_token, "temp_admin")
    await ws_temp.send(json.dumps({
        "action": "admin",
        "admin_action": "set_role",
        "target_token": admin_token,
        "new_role": "admin"
    }))
    r = json.loads(await ws_temp.recv())
    print(f"⚠️  预期失败（还没管理员）：{r}")
    await ws_temp.close()
    
    # 手动设置数据库（首次管理员）
    import sqlite3
    from pathlib import Path
    DB_PATH = Path(__file__).parent.parent / "chatroom-project" / "chatroom.db"
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE openclaws SET role='admin' WHERE identity_token=?", (admin_token,))
    conn.commit()
    conn.close()
    print("✅ 手动设置管理员角色完成")
    
    # 用管理员身份连接
    print("\n📞 管理员连接中...")
    admin_ws, r = await connect(admin_token, "管理员")
    print(f"✅ {r['message']}")
    
    # 普通用户连接
    print("\n📞 普通用户连接中...")
    user_token = await register_only("user1")
    user_ws, r = await connect(user_token, "普通用户")
    print(f"✅ {r['message']}")
    
    # 测试获取配置
    print("\n📊 获取聊天室配置...")
    await admin_ws.send(json.dumps({
        "action": "admin",
        "admin_action": "get_config"
    }))
    r = json.loads(await admin_ws.recv())
    if "config" in r:
        print(f"📋 密码={r['config'].get('room_password')}, 人数限制={r['config'].get('max_members')}")
    
    # 测试修改密码
    print("\n🔐 测试修改密码...")
    await admin_ws.send(json.dumps({
        "action": "admin",
        "admin_action": "change_password",
        "new_password": "new-password-2026"
    }))
    r = json.loads(await admin_ws.recv())
    print(f"✅ {r.get('message', r)}")
    
    # 测试非管理员操作（应该失败）
    print("\n❌ 测试普通用户尝试管理员操作...")
    await user_ws.send(json.dumps({
        "action": "admin",
        "admin_action": "kick",
        "target_bot": "someone"
    }))
    r = json.loads(await user_ws.recv())
    if "error" in r:
        print(f"✅ 正确拒绝：{r['error']}")
    
    # 恢复密码
    print("\n🔐 恢复默认密码...")
    await admin_ws.send(json.dumps({
        "action": "admin",
        "admin_action": "change_password",
        "new_password": PASSWORD
    }))
    r = json.loads(await admin_ws.recv())
    print(f"✅ {r.get('message', r)}")
    
    # 测试查看封禁列表
    print("\n📋 查看封禁列表...")
    await admin_ws.send(json.dumps({
        "action": "admin",
        "admin_action": "list_banned"
    }))
    r = json.loads(await admin_ws.recv())
    if "banned" in r:
        print(f"📋 封禁用户：{len(r['banned'])} 人")
    
    # 测试封禁用户
    print("\n🚫 测试封禁用户...")
    await admin_ws.send(json.dumps({
        "action": "admin",
        "admin_action": "ban",
        "target_token": user_token
    }))
    r = json.loads(await admin_ws.recv())
    print(f"✅ {r.get('message', r)}")
    
    # 检查用户是否被断开
    try:
        msg = await asyncio.wait_for(user_ws.recv(), timeout=2)
        data = json.loads(msg)
        if "error" in data:
            print(f"✅ 用户收到通知：{data['error']}")
    except asyncio.TimeoutError:
        print("⚠️  用户未收到通知")
    
    # 解封用户
    print("\n✅ 解封用户...")
    await admin_ws.send(json.dumps({
        "action": "admin",
        "admin_action": "unban",
        "target_token": user_token
    }))
    r = json.loads(await admin_ws.recv())
    print(f"✅ {r.get('message', r)}")
    
    # 测试设置人数限制
    print("\n👥 测试修改人数限制...")
    await admin_ws.send(json.dumps({
        "action": "admin",
        "admin_action": "set_max_members",
        "max_members": "100"
    }))
    r = json.loads(await admin_ws.recv())
    print(f"✅ {r.get('message', r)}")
    
    # 恢复人数限制
    await admin_ws.send(json.dumps({
        "action": "admin",
        "admin_action": "set_max_members",
        "max_members": "50"
    }))
    await admin_ws.recv()
    
    # 清理
    await admin_ws.close()
    await user_ws.close()
    
    print("\n🎉 管理功能测试完成！")


if __name__ == "__main__":
    asyncio.run(test_admin_features())
