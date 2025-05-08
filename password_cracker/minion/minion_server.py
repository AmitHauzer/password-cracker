"""
Minion server for password cracking.
"""

import logging
import uuid
import hashlib
import httpx
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from contextlib import asynccontextmanager
import asyncio
from datetime import datetime
from typing import Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
MASTER_URL = "http://localhost:8000"
HEARTBEAT_INTERVAL = 5  # seconds
MAX_RETRIES = 5
RETRY_DELAY = 5  # seconds


class TaskStatus:
    """Task status tracking."""

    def __init__(self):
        self.current_task: Optional[CrackTask] = None
        self.start_time: Optional[datetime] = None
        self.progress: int = 0
        self.status: str = "idle"
        self.last_heartbeat: Optional[datetime] = None


class CrackTask(BaseModel):
    """Task model for cracking a hash."""
    hash: str
    start: int
    end: int


def calculate(start: int, end: int, target_hash: str, task_status: TaskStatus) -> str | None:
    """Calculate MD5 hashes for phone numbers in the given range."""
    total = end - start
    for i in range(start, end):
        # Update progress every 1%
        if (i - start) % (total // 100) == 0:
            task_status.progress = ((i - start) * 100) // total
            logger.info(f"Progress: {task_status.progress}%")

        # Format as phone number: 050-XXXXXXX
        phone = f"050-{i:07d}"
        hash_value = hashlib.md5(phone.encode()).hexdigest()
        if hash_value == target_hash:
            return phone
    return None


async def connect_to_master(minion_id: str) -> bool:
    """Attempt to connect to the master server."""
    retries = 0
    while retries < MAX_RETRIES:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(f"{MASTER_URL}/register/{minion_id}")
                if response.status_code == 200:
                    logger.info(
                        f"Successfully registered with master as {minion_id}")
                    return True
                else:
                    logger.error(
                        f"Failed to register with master: {response.status_code}")
        except Exception as e:
            logger.warning(f"Connection attempt {retries + 1} failed: {e}")

        retries += 1
        if retries < MAX_RETRIES:
            logger.info(f"Retrying in {RETRY_DELAY} seconds...")
            await asyncio.sleep(RETRY_DELAY)

    logger.error("Failed to connect to master after maximum retries")
    return False


async def send_heartbeat(minion_id: str) -> bool:
    """Send heartbeat to master server."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{MASTER_URL}/heartbeat/{minion_id}")
            if response.status_code == 200:
                task_status.last_heartbeat = datetime.now()
                return True
            logger.error(f"Heartbeat failed: {response.status_code}")
    except Exception as e:
        logger.error(f"Heartbeat error: {e}")
    return False


async def send_heartbeat_loop():
    """Send periodic heartbeats to master."""
    while True:
        await send_heartbeat(minion_id)
        await asyncio.sleep(HEARTBEAT_INTERVAL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler."""
    # Startup
    if not await connect_to_master(minion_id):
        logger.error("Failed to connect to master, shutting down")
        raise RuntimeError("Failed to connect to master")

    # Start heartbeat task
    heartbeat_task = asyncio.create_task(send_heartbeat_loop())

    yield

    # Shutdown
    heartbeat_task.cancel()
    try:
        await heartbeat_task
    except asyncio.CancelledError:
        pass
    logger.info("Shutting down minion")

app = FastAPI(lifespan=lifespan)
minion_id = str(uuid.uuid4())
task_status = TaskStatus()


@app.get("/status")
async def get_status():
    """Get current minion status."""
    return {
        "minion_id": minion_id,
        "status": task_status.status,
        "progress": task_status.progress,
        "current_task": task_status.current_task.dict() if task_status.current_task else None,
        "last_heartbeat": task_status.last_heartbeat,
        "uptime": (datetime.now() - task_status.start_time).total_seconds() if task_status.start_time else 0
    }


@app.post("/crack")
async def crack_hash(task: CrackTask):
    """Crack a hash in the given range."""
    logger.info(
        f"Received task: hash={task.hash}, range={task.start}-{task.end}")

    # Update task status
    task_status.current_task = task
    task_status.start_time = datetime.now()
    task_status.status = "processing"
    task_status.progress = 0

    try:
        result = calculate(task.start, task.end, task.hash, task_status)

        if result:
            logger.info(f"Found password: {result}")
            task_status.status = "completed"
            return {"status": "success", "password": result}
        else:
            logger.info("No password found in range")
            task_status.status = "completed"
            return {"status": "not_found"}
    except Exception as e:
        logger.error(f"Error processing task: {e}")
        task_status.status = "failed"
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        task_status.progress = 100

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
