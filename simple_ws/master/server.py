"""
Simple master server that sends messages to minions.
"""

import asyncio
import logging
from typing import Dict, Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Store connected minions
connected_minions: Dict[str, WebSocket] = {}


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, minion_id: str):
        await websocket.accept()
        self.active_connections[minion_id] = websocket
        logger.info(f"Minion {minion_id} connected")

    def disconnect(self, minion_id: str):
        if minion_id in self.active_connections:
            del self.active_connections[minion_id]
            logger.info(f"Minion {minion_id} disconnected")

    async def send_message(self, minion_id: str, message: str):
        if minion_id in self.active_connections:
            await self.active_connections[minion_id].send_text(message)
            logger.info(f"Sent message to minion {minion_id}: {message}")
        else:
            logger.error(f"Minion {minion_id} not found")


manager = ConnectionManager()


@app.websocket("/ws/{minion_id}")
async def websocket_endpoint(websocket: WebSocket, minion_id: str):
    await manager.connect(websocket, minion_id)
    try:
        while True:
            # Wait for response from minion
            response = await websocket.receive_text()
            logger.info(f"Received from minion {minion_id}: {response}")
    except WebSocketDisconnect:
        manager.disconnect(minion_id)


@app.get("/minions")
async def get_minions():
    """Get list of connected minions."""
    return {"minions": list(manager.active_connections.keys())}


@app.post("/send/{minion_id}")
async def send_to_minion(minion_id: str, message: str):
    """Send a message to a specific minion."""
    await manager.send_message(minion_id, message)
    return {"status": "message sent"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
