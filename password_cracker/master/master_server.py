"""
Master server for password cracking.
"""

import logging
import httpx
import uvicorn
import asyncio
from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Dict, Optional, List, AsyncGenerator, Tuple
from datetime import datetime
import hashlib
import tempfile
import os


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Constants
TOTAL_RANGE = 100_000_000  # 050-0000000 to 059-9999999 (10^8 numbers)
REQUEST_TIMEOUT = 300.0  # 5 minutes timeout for requests


class Minion:
    """Minion information."""

    def __init__(self, minion_id: str, port: int):
        self.id = minion_id
        self.port = port
        self.last_heartbeat = datetime.now()
        self.is_active = True
        self.current_task: Optional[Task] = None
        self.status: str = "idle"
        self.progress: int = 0
        logger.debug(f"Created new minion: {self.id} on port {self.port}")


class Task:
    """Task information."""

    def __init__(self, hash_value: str):
        self.hash = hash_value
        self.start_time = datetime.now()
        self.status = "pending"
        self.assigned_minions: List[str] = []
        self.result: Optional[str] = None
        logger.debug(f"Created new task for hash: {hash_value}")


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
    port: int
    status: str
    progress: int
    current_task: Optional[dict] = None
    last_heartbeat: datetime


# Global variables
app = FastAPI()
minions: Dict[str, Minion] = {}
active_tasks: Dict[str, Task] = {}
current_hash_file: Optional[str] = None
is_processing: bool = False


@app.post("/upload-hashes")
async def upload_hashes(file: UploadFile = File(...)):
    """Upload a file containing hashes to process."""
    global current_hash_file, is_processing
    logger.info(f"Received file upload request: {file.filename}")

    if is_processing:
        logger.warning("Already processing a file")
        raise HTTPException(
            status_code=400, detail="Already processing a file")

    # Save uploaded file
    try:
        with tempfile.NamedTemporaryFile(delete=False, mode='w') as temp_file:
            content = await file.read()
            temp_file.write(content.decode())
            current_hash_file = temp_file.name
            logger.info(f"Saved hash file to {current_hash_file}")

        # Start processing
        is_processing = True
        asyncio.create_task(process_all_hashes())
        return {"status": "success", "message": "File uploaded and processing started"}
    except Exception as e:
        logger.error(f"Error processing uploaded file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def read_hashes() -> AsyncGenerator[str, None]:
    """Read hashes from file one by one."""
    global current_hash_file, is_processing
    logger.debug(f"Starting to read hashes from file: {current_hash_file}")

    if not current_hash_file:
        logger.error("No hash file available")
        return

    try:
        with open(current_hash_file, 'r') as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if line and not line.startswith('#'):
                    logger.debug(f"Read hash: {line}")
                    yield line
                    await asyncio.sleep(0)  # Allow other tasks to run
    except FileNotFoundError:
        logger.error(f"Hash file not found: {current_hash_file}")
        raise
    finally:
        # Cleanup
        try:
            os.unlink(current_hash_file)
            current_hash_file = None
            is_processing = False
            logger.debug("Cleaned up hash file")
        except Exception as e:
            logger.error(f"Error cleaning up hash file: {e}")


async def verify_password(phone: str, target_hash: str) -> bool:
    """Verify if a phone number matches the target hash."""
    hash_value = hashlib.md5(phone.encode()).hexdigest()
    return hash_value == target_hash


async def process_minion_range(minion_id: str, minion: Minion, start: int, end: int, target_hash: str, task: Task) -> Optional[str]:
    """Process a range of numbers on a specific minion."""
    async with httpx.AsyncClient() as client:
        try:
            logger.debug(
                f"Sending crack request to minion {minion_id} on port {minion.port}")
            response = await client.post(
                f"http://localhost:{minion.port}/crack",
                json={
                    "hash": target_hash,
                    "start": start,
                    "end": end
                },
                timeout=REQUEST_TIMEOUT
            )
            if response.status_code == 200:
                result = response.json()
                logger.debug(
                    f"Received response from minion {minion_id}: {result}")
                if result["status"] == "success":
                    phone = result["password"]
                    if await verify_password(phone, target_hash):
                        task.status = "completed"
                        task.result = phone
                        logger.info(
                            f"Found password for hash {target_hash}: {phone} by minion {minion_id}")
                        return phone
        except Exception as e:
            logger.error(f"Error from minion {minion_id}: {e}")
            minion.is_active = False
            minion.status = "failed"
            task.assigned_minions.remove(minion_id)
    return None


def split_range(total_range: int, num_minions: int) -> List[Tuple[int, int]]:
    """Split the total range into parts for each minion."""
    part_size = max(1, total_range // num_minions)
    ranges = []
    for i in range(num_minions):
        start = i * part_size
        end = start + part_size if i < num_minions - 1 else total_range
        ranges.append((start, end))
    return ranges


async def process_hash(hash_value: str) -> Optional[str]:
    """Process a single hash using available minions."""
    logger.info(f"Processing hash: {hash_value}")

    if not minions:
        logger.error("No minions available")
        return None

    # Create new task
    task = Task(hash_value)
    task_id = str(len(active_tasks))
    active_tasks[task_id] = task
    logger.debug(f"Created task {task_id} for hash {hash_value}")

    # Split the range among available minions
    ranges = split_range(TOTAL_RANGE, len(minions))
    logger.info(
        f"Split range into {len(ranges)} parts for {len(minions)} minions")

    # Create tasks for each minion
    tasks = []
    for (minion_id, minion), (start, end) in zip(minions.items(), ranges):
        if not minion.is_active:
            logger.warning(f"Minion {minion_id} is not active, skipping")
            continue

        minion.current_task = task
        minion.status = "processing"
        task.assigned_minions.append(minion_id)
        logger.info(
            f"Assigned range {start:,}-{end:,} to minion {minion_id} on port {minion.port}")
        tasks.append(process_minion_range(
            minion_id, minion, start, end, hash_value, task))

    # Wait for any minion to find the password
    for completed_task in asyncio.as_completed(tasks):
        result = await completed_task
        if result:
            return result

    task.status = "not_found"
    logger.info(
        f"No password found for hash {hash_value} after checking all ranges")
    return None


async def process_all_hashes():
    """Process all hashes from the file."""
    logger.info("Starting to process all hashes")
    async for hash_value in read_hashes():
        logger.info(f"Processing hash: {hash_value}")
        result = await process_hash(hash_value)
        if result:
            logger.info(f"Found password for {hash_value}: {result}")
        else:
            logger.info(f"No password found for {hash_value}")


@app.on_event("startup")
async def startup_event():
    """Start processing hashes on startup."""
    logger.info("Master server starting up")
    asyncio.create_task(process_all_hashes())


@app.post("/register/{minion_id}")
async def register_minion(minion_id: str, port: int):
    """Register a new minion."""
    logger.info(f"Registering minion {minion_id} on port {port}")
    minions[minion_id] = Minion(minion_id, port)
    return {"status": "registered"}


@app.post("/heartbeat/{minion_id}")
async def heartbeat(minion_id: str):
    """Update minion heartbeat."""
    if minion_id in minions:
        minions[minion_id].last_heartbeat = datetime.now()
        minions[minion_id].is_active = True
        return {"status": "ok"}
    logger.warning(f"Heartbeat from unknown minion: {minion_id}")
    raise HTTPException(status_code=404, detail="Minion not found")


@app.get("/minions")
async def get_minions():
    """Get list of registered minions and their status."""
    logger.debug("Getting minion status")
    return {
        "minions": [
            MinionStatus(
                minion_id=minion.id,
                port=minion.port,
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
    logger.info(f"Received crack request for hash: {request.hash}")

    if not minions:
        logger.error("No minions available")
        return CrackResponse(
            status="error",
            error="No minions available"
        )

    # Create new task
    task = Task(request.hash)
    task_id = str(len(active_tasks))
    active_tasks[task_id] = task
    logger.debug(f"Created task {task_id} for hash {request.hash}")

    # Split the range among available minions
    part_size = TOTAL_RANGE // len(minions)
    ranges = []
    for i in range(len(minions)):
        start = i * part_size
        end = start + part_size if i < len(minions) - 1 else TOTAL_RANGE
        ranges.append((start, end))
    logger.debug(f"Split range into {len(ranges)} parts")

    # Create tasks for each minion
    for (minion_id, minion), (start, end) in zip(minions.items(), ranges):
        if not minion.is_active:
            logger.warning(f"Minion {minion_id} is not active, skipping")
            continue

        minion.current_task = task
        minion.status = "processing"
        task.assigned_minions.append(minion_id)
        logger.debug(f"Assigned range {start}-{end} to minion {minion_id}")

        async with httpx.AsyncClient() as client:
            try:
                logger.debug(
                    f"Sending crack request to minion {minion_id} on port {minion.port}")
                response = await client.post(
                    f"http://localhost:{minion.port}/crack",
                    json={
                        "hash": request.hash,
                        "start": start,
                        "end": end
                    },
                    timeout=REQUEST_TIMEOUT
                )
                if response.status_code == 200:
                    result = response.json()
                    logger.debug(
                        f"Received response from minion {minion_id}: {result}")
                    if result["status"] == "success":
                        # Verify the result
                        phone = result["password"]
                        hash_value = hashlib.md5(phone.encode()).hexdigest()
                        if hash_value == request.hash:
                            task.status = "completed"
                            task.result = phone
                            logger.info(
                                f"Found password for hash {request.hash}: {phone}")
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
    logger.info(f"No password found for hash {request.hash}")
    return CrackResponse(
        status="not_found",
        error="Password not found in any range",
        task_id=task_id
    )


@app.get("/task/{task_id}")
async def get_task_status(task_id: str):
    """Get status of a specific task."""
    logger.debug(f"Getting status for task {task_id}")
    if task_id not in active_tasks:
        logger.warning(f"Task {task_id} not found")
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
    logger.info("Starting master server on port 8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
