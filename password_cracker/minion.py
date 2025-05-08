"""
Minion server for the password cracker.
"""

import argparse
import asyncio
import hashlib
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, Optional, Any

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import httpx
import websockets

from .websocket import Message, TaskMessage, StatusMessage, ResultMessage, HeartbeatMessage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
minion_id = str(uuid.uuid4())
current_task: Optional[Dict] = None
websocket: Optional[websockets.WebSocketClientProtocol] = None
MASTER_URL = "ws://localhost:8000/ws"  # WebSocket URL for master


def calculate(start: int, end: int, target_hash: str) -> Optional[str]:
    """Calculate MD5 hashes for phone numbers in the given range."""
    for i in range(start, end):
        # Format as phone number: 050-XXXXXXX
        phone = f"050-{i:07d}"
        hash_value = hashlib.md5(phone.encode()).hexdigest()
        if hash_value == target_hash:
            return phone
    return None


async def send_heartbeat():
    """Send periodic heartbeat to master."""
    while True:
        if websocket:
            try:
                message = HeartbeatMessage(
                    type="heartbeat",
                    data={"timestamp": datetime.now().timestamp()}
                )
                await websocket.send(json.dumps(message.model_dump()))
            except Exception as e:
                logger.error(f"Error sending heartbeat: {e}")
        await asyncio.sleep(5)


async def process_task(task_id: str, hash_value: str, start: int, end: int):
    """Process a cracking task."""
    global current_task
    try:
        current_task = {
            "task_id": task_id,
            "hash": hash_value,
            "start": start,
            "end": end,
            "status": "IN_PROGRESS"
        }

        # Send status update
        if websocket:
            message = StatusMessage(
                type="status",
                data={
                    "status": "working",
                    "progress": 0.0
                }
            )
            await websocket.send(json.dumps(message.model_dump()))

        # Start calculation
        start_time = datetime.now()
        password = calculate(start, end, hash_value)
        time_taken = (datetime.now() - start_time).total_seconds()

        # Send result
        if websocket:
            message = ResultMessage(
                type="result",
                data={
                    "task_id": task_id,
                    "password": password,
                    "time_taken": time_taken
                }
            )
            await websocket.send(json.dumps(message.model_dump()))

        current_task = None

    except Exception as e:
        logger.error(f"Error processing task: {e}")
        if websocket:
            message = ResultMessage(
                type="result",
                data={
                    "task_id": task_id,
                    "password": None,
                    "time_taken": 0,
                    "error": str(e)
                }
            )
            await websocket.send(json.dumps(message.model_dump()))
        current_task = None


async def connect_to_master():
    """Connect to master server with retry logic."""
    global websocket
    while True:
        try:
            async with httpx.AsyncClient() as client:
                # First try to connect to master's HTTP endpoint to check if it's up
                response = await client.get("http://localhost:8000/status")
                if response.status_code == 200:
                    logger.info(
                        "Master server is up, attempting WebSocket connection...")
                    break
        except Exception:
            logger.warning(
                "Master server not available, retrying in 5 seconds...")
            await asyncio.sleep(5)

    while True:
        try:
            # Create WebSocket connection using websockets library
            async with websockets.connect(f"{MASTER_URL}/{minion_id}") as ws:
                websocket = ws
                logger.info(
                    f"Connected to master with ID: {minion_id}")

                # Start heartbeat task
                heartbeat_task = asyncio.create_task(send_heartbeat())

                while True:
                    try:
                        data = await ws.recv()
                        message = Message(**json.loads(data))

                        if message.type == "task":
                            task_data = message.data
                            asyncio.create_task(process_task(
                                task_data["task_id"],
                                task_data["hash"],
                                task_data["range"]["start"],
                                task_data["range"]["end"]
                            ))
                    except websockets.exceptions.ConnectionClosed:
                        logger.info(
                            "WebSocket disconnected, attempting to reconnect...")
                        break
                    except Exception as e:
                        logger.error(f"Error processing message: {e}")
                        break

        except Exception as e:
            logger.error(f"Connection error: {e}")
            websocket = None
            logger.info("Retrying connection in 5 seconds...")
            await asyncio.sleep(5)


@app.on_event("startup")
async def startup_event():
    """Start connection to master on startup."""
    asyncio.create_task(connect_to_master())


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Password Cracker Minion")
    parser.add_argument("--port", type=int, default=8001,
                        help="Port to run the minion on")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    uvicorn.run(app, host="0.0.0.0", port=args.port)
