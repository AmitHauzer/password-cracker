"""
Master server for the password cracker.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel

from .websocket import WebSocketManager, Message, TaskMessage, ResultMessage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
manager = WebSocketManager()

# Store task information
tasks: Dict[str, Dict] = {}
results: Dict[str, Dict] = {}


class CrackRequest(BaseModel):
    """Request model for cracking a hash."""
    hash: str


class CrackResponse(BaseModel):
    """Response model for cracking a hash."""
    task_id: str
    status: str
    result: Optional[str] = None


@app.websocket("/ws/{minion_id}")
async def websocket_endpoint(websocket: WebSocket, minion_id: str):
    """WebSocket endpoint for minion communication."""
    await manager.connect(websocket, minion_id)
    logger.info(f"Minion {minion_id} connected to WebSocket endpoint")

    try:
        while True:
            message = await manager.receive_message(minion_id)
            if message is None:
                break

            if message.type == "result":
                task_id = message.data["task_id"]
                if task_id in tasks:
                    tasks[task_id]["completed"] = True
                    results[task_id] = message.data
                    logger.info(
                        f"Received result for task {task_id}: {message.data}")
    except WebSocketDisconnect:
        logger.info(f"Minion {minion_id} disconnected")
        manager.disconnect(minion_id)
    except Exception as e:
        logger.error(
            f"Error in websocket connection with minion {minion_id}: {e}")
        manager.disconnect(minion_id)


@app.post("/crack", response_model=CrackResponse)
async def crack_hash(request: CrackRequest):
    """Submit a hash to crack."""
    task_id = str(uuid.uuid4())
    tasks[task_id] = {
        "hash": request.hash,
        "started_at": datetime.now().timestamp(),
        "completed": False,
        "assigned_to": None
    }

    # Find available minion
    active_minions = manager.get_active_minions()
    if not active_minions:
        raise HTTPException(status_code=503, detail="No minions available")

    # Assign task to first available minion
    minion_id = next(iter(active_minions))
    tasks[task_id]["assigned_to"] = minion_id

    # Calculate range for this minion
    start = 0
    end = 1000000  # Adjust based on your needs

    # Send task to minion
    try:
        await manager.send_task(minion_id, task_id, request.hash, start, end)
        logger.info(f"Task {task_id} assigned to minion {minion_id}")
    except Exception as e:
        logger.error(f"Error sending task to minion {minion_id}: {e}")
        raise HTTPException(
            status_code=503, detail=f"Error assigning task: {str(e)}")

    return CrackResponse(
        task_id=task_id,
        status="processing"
    )


@app.get("/status/{task_id}", response_model=CrackResponse)
async def get_status(task_id: str):
    """Get status of a cracking task."""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task = tasks[task_id]
    if task["completed"]:
        return CrackResponse(
            task_id=task_id,
            status="completed",
            result=results[task_id].get("password")
        )

    return CrackResponse(
        task_id=task_id,
        status="processing"
    )


@app.get("/minions")
async def get_minions():
    """Get status of all minions."""
    return {
        "minions": manager.get_active_minions()
    }


@app.get("/status")
async def get_system_status():
    """Get overall system status."""
    active_minions = manager.get_active_minions()
    return {
        "active_minions": len(active_minions),
        "pending_tasks": sum(1 for task in tasks.values() if not task["completed"]),
        "completed_tasks": sum(1 for task in tasks.values() if task["completed"]),
        "failed_tasks": 0  # Implement if needed
    }


async def cleanup_inactive_minions():
    """Periodically clean up inactive minions."""
    while True:
        inactive_minions = manager.get_inactive_minions()
        for minion_id in inactive_minions:
            logger.info(f"Removing inactive minion: {minion_id}")
            manager.disconnect(minion_id)
        await asyncio.sleep(10)


@app.on_event("startup")
async def startup_event():
    """Start background tasks on server startup."""
    asyncio.create_task(cleanup_inactive_minions())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
