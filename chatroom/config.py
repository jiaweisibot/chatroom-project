"""
Chatroom 配置管理
"""

import os
import json
from pathlib import Path
from typing import Optional

# 默认配置
DEFAULT_CONFIG = {
    "host": "0.0.0.0",
    "port": 8765,
    "room_password": "claw-yiwei-2026",
    "max_members": 50,
    "hub_url": "ws://localhost:8765",
}

CONFIG_FILE = Path.home() / ".openclaw" / "chatroom-config.json"


def load_config() -> dict:
    """加载配置"""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r") as f:
            return {**DEFAULT_CONFIG, **json.load(f)}
    return DEFAULT_CONFIG.copy()


def save_config(config: dict):
    """保存配置"""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def get_config(key: str, default=None):
    """获取配置项"""
    config = load_config()
    return config.get(key, default)


# 快捷访问
HOST = get_config("host", DEFAULT_CONFIG["host"])
PORT = get_config("port", DEFAULT_CONFIG["port"])
ROOM_PASSWORD = get_config("room_password", DEFAULT_CONFIG["room_password"])
MAX_MEMBERS = get_config("max_members", DEFAULT_CONFIG["max_members"])
HUB_URL = get_config("hub_url", DEFAULT_CONFIG["hub_url"])