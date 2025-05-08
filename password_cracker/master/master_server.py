"""
Master server for password cracking.
"""

import logging
import httpx
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional, List
import asyncio
from datetime import datetime, timedelta
import hashlib

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
HEARTBEAT_TIMEOUT = 30  # seconds
TOTAL_RANGE = 10_000_000  # 050-0000000 to 050-9999999
MINION_PORT = 8001


class Minion:
    """Minion information."""

    def __init__(self, minion_id: str):
        self.id = minion_id
        self.last_heartbeat = datetime.now()
        self.is_active = True
        self.current_task: Optional[Task] = None
        self.status: str = "idle"
        self.progress: int = 0


class Task:
    """Task information."""

    def __init__(self, hash_value: str):
        self.hash = hash_value
        self.start_time = datetime.now()
        self.status = "pending"
        self.assigned_minions: List[str] = []
        self.result: Optional[str] = None


class CrackRequest(BaseModel):
    """Request model for cracking a hash."""
    hash: str


class CrackResponse(BaseModel):
    """Response model for cracking a hash."""
    status: str
    password: Optional[str] = None
    error: Optional[str] = None
    task_id: Optional[str] = None


class MinionStatus(BaseModel):
    """Response model for minion status."""
    minion_id: str
    status: str
    progress: int
    current_task: Optional[dict] = None
    last_heartbeat: datetime


app = FastAPI()
minions: Dict[str, Minion] = {}
active_tasks: Dict[str, Task] = {}


async def cleanup_inactive_minions():
    """Remove inactive minions."""
    while True:
        now = datetime.now()
        for minion_id, minion in list(minions.items()):
            if now - minion.last_heartbeat > timedelta(seconds=HEARTBEAT_TIMEOUT):
                logger.info(f"Removing inactive minion: {minion_id}")
                if minion.current_task:
                    # Reassign task if minion was working on one
                    task = minion.current_task
                    task.assigned_minions.remove(minion_id)
                    if not task.assigned_minions:
                        task.status = "pending"
                del minions[minion_id]
        await asyncio.sleep(5)


@app.on_event("startup")
async def startup_event():
    """Start cleanup task on startup."""
    asyncio.create_task(cleanup_inactive_minions())


@app.post("/register/{minion_id}")
async def register_minion(minion_id: str):
    """Register a new minion."""
    minions[minion_id] = Minion(minion_id)
    logger.info(f"Registered minion: {minion_id}")
    return {"status": "registered"}


@app.post("/heartbeat/{minion_id}")
async def heartbeat(minion_id: str):
    """Update minion heartbeat."""
    if minion_id in minions:
        minions[minion_id].last_heartbeat = datetime.now()
        minions[minion_id].is_active = True
        return {"status": "ok"}
    raise HTTPException(status_code=404, detail="Minion not found")


@app.get("/minions")
async def get_minions():
    """Get list of registered minions and their status."""
    return {
        "minions": [
            MinionStatus(
                minion_id=minion.id,
                status=minion.status,
                progress=minion.progress,
                current_task=minion.current_task.__dict__ if minion.current_task else None,
                last_heartbeat=minion.last_heartbeat
            ).model_dump()
            for minion in minions.values()
        ]
    }


@app.post("/crack", response_model=CrackResponse)
async def crack_hash(request: CrackRequest):
    """Crack a hash using available minions."""
    if not minions:
        return CrackResponse(
            status="error",
            error="No minions available"
        )

    # Create new task
    task = Task(request.hash)
    task_id = str(len(active_tasks))
    active_tasks[task_id] = task

    # Split the range among available minions
    part_size = TOTAL_RANGE // len(minions)
    ranges = []
    for i in range(len(minions)):
        start = i * part_size
        end = start + part_size if i < len(minions) - 1 else TOTAL_RANGE
        ranges.append((start, end))

    # Create tasks for each minion
    for (minion_id, minion), (start, end) in zip(minions.items(), ranges):
        if not minion.is_active:
            continue

        minion.current_task = task
        minion.status = "processing"
        task.assigned_minions.append(minion_id)

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"http://localhost:{MINION_PORT}/crack",
                    json={
                        "hash": request.hash,
                        "start": start,
                        "end": end
                    },
                    timeout=30.0
                )
                if response.status_code == 200:
                    result = response.json()
                    if result["status"] == "success":
                        # Verify the result
                        phone = result["password"]
                        hash_value = hashlib.md5(phone.encode()).hexdigest()
                        if hash_value == request.hash:
                            task.status = "completed"
                            task.result = phone
                            return CrackResponse(
                                status="success",
                                password=phone,
                                task_id=task_id
                            )
            except Exception as e:
                logger.error(f"Error from minion {minion_id}: {e}")
                minion.is_active = False
                minion.status = "failed"
                task.assigned_minions.remove(minion_id)

    task.status = "not_found"
    return CrackResponse(
        status="not_found",
        error="Password not found in any range",
        task_id=task_id
    )


@app.get("/task/{task_id}")
async def get_task_status(task_id: str):
    """Get status of a specific task."""
    if task_id not in active_tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task = active_tasks[task_id]
    return {
        "task_id": task_id,
        "hash": task.hash,
        "status": task.status,
        "start_time": task.start_time,
        "assigned_minions": task.assigned_minions,
        "result": task.result
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
