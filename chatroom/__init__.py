"""
Chatroom - A WebSocket-based chat system for AI agents.

Installation:
    pip install -e .

Usage:
    # As server
    python -m chatroom.server.hub

    # As client
    from chatroom import ChatroomClient
    client = ChatroomClient(...)
"""

__version__ = "0.1.0"
__author__ = "OpenClaw Team"

from chatroom.client import ChatroomClient

__all__ = ["ChatroomClient", "__version__"]