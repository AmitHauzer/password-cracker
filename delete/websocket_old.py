"""
WebSocket communication module for master-minion architecture.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, Optional, Any

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class Message(BaseModel):
    """Base message model."""
    type: str
    data: Dict[str, Any]


class TaskMessage(Message):
    """Task assignment message."""
    type: str = "task"
    data: Dict[str, Any] = {
        "task_id": str,
        "hash": str,
        "range": Dict[str, int]
    }


class StatusMessage(Message):
    """Status update message."""
    type: str = "status"
    data: Dict[str, Any] = {
        "status": str,
        "progress": float
    }


class ResultMessage(Message):
    """Result message."""
    type: str = "result"
    data: Dict[str, Any] = {
        "task_id": str,
        "password": Optional[str],
        "time_taken": float
    }


class HeartbeatMessage(Message):
    """Heartbeat message."""
    type: str = "heartbeat"
    data: Dict[str, Any] = {
        "timestamp": float
    }


class WebSocketManager:
    """Manages WebSocket connections and message handling."""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.minion_status: Dict[str, Dict] = {}
        self.last_heartbeat: Dict[str, float] = {}

    async def connect(self, websocket: WebSocket, minion_id: str):
        """Connect a new minion."""
        await websocket.accept()
        self.active_connections[minion_id] = websocket
        self.minion_status[minion_id] = {"status": "connected", "progress": 0}
        self.last_heartbeat[minion_id] = datetime.now().timestamp()
        logger.info(f"Minion {minion_id} connected")

    def disconnect(self, minion_id: str):
        """Disconnect a minion."""
        if minion_id in self.active_connections:
            del self.active_connections[minion_id]
        if minion_id in self.minion_status:
            del self.minion_status[minion_id]
        if minion_id in self.last_heartbeat:
            del self.last_heartbeat[minion_id]
        logger.info(f"Minion {minion_id} disconnected")

    async def send_task(self, minion_id: str, task_id: str, hash_value: str, start: int, end: int):
        """Send a task to a minion."""
        if minion_id not in self.active_connections:
            raise ValueError(f"Minion {minion_id} not connected")

        message = TaskMessage(
            data={
                "task_id": task_id,
                "hash": hash_value,
                "range": {"start": start, "end": end}
            }
        )
        await self.active_connections[minion_id].send_json(message.dict())
        logger.info(f"Sent task {task_id} to minion {minion_id}")

    async def broadcast(self, message: Message):
        """Broadcast a message to all connected minions."""
        for minion_id, connection in self.active_connections.items():
            try:
                await connection.send_json(message.dict())
            except Exception as e:
                logger.error(f"Error broadcasting to minion {minion_id}: {e}")

    async def receive_message(self, minion_id: str) -> Optional[Message]:
        """Receive a message from a minion."""
        if minion_id not in self.active_connections:
            return None

        try:
            data = await self.active_connections[minion_id].receive_json()
            message = Message(**data)

            if message.type == "heartbeat":
                self.last_heartbeat[minion_id] = datetime.now().timestamp()
            elif message.type == "status":
                self.minion_status[minion_id].update(message.data)

            return message
        except WebSocketDisconnect:
            self.disconnect(minion_id)
            return None
        except Exception as e:
            logger.error(
                f"Error receiving message from minion {minion_id}: {e}")
            return None

    def get_active_minions(self) -> Dict[str, Dict]:
        """Get status of all active minions."""
        return {
            minion_id: {
                "status": status["status"],
                "progress": status["progress"],
                "last_heartbeat": self.last_heartbeat.get(minion_id, 0)
            }
            for minion_id, status in self.minion_status.items()
        }

    def get_inactive_minions(self, timeout: float = 30.0) -> list[str]:
        """Get list of minions that haven't sent a heartbeat in timeout seconds."""
        now = datetime.now().timestamp()
        return [
            minion_id
            for minion_id, last_time in self.last_heartbeat.items()
            if now - last_time > timeout
        ]
