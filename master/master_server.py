"""
Master server for the password cracker.
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import RedirectResponse
from typing import Dict
import hashlib
import asyncio
from pathlib import Path
import json
import uvicorn

from config import MASTER_SERVER_PORT, setup_logger, parse_args
from .utils.models import HashTask, MinionRegistration
from .utils.utils import get_hash_from_file, save_temp_file

# Parse command line arguments
args = parse_args("Password Cracker Master Server")

logger = setup_logger("master_server", log_level=args.log_level)

# Create FastAPI app
app = FastAPI(title="Password Cracker Master Server")

# Store registered minions
minions: Dict[str, dict] = {}

# Store tasks
tasks: Dict[str, HashTask] = {}


@app.get("/")
async def root():
    return RedirectResponse(url="/docs")


@app.post("/register")
async def register_minion(minion: MinionRegistration):
    """Register a new minion server."""
    minions[minion.minion_id] = {
        "host": minion.host,
        "port": minion.port,
        "capabilities": minion.capabilities,
        "status": "active"
    }
    logger.info(f"Minion {minion.minion_id} registered successfully")
    return {"status": "success", "message": f"Minion {minion.minion_id} registered successfully"}


@app.post("/upload-hashes")
async def upload_hashes(file: UploadFile = File(...)):
    """Upload a file containing MD5 hashes."""
    try:
        # Save the uploaded file temporarily
        temp_file = await save_temp_file(file)

        # Process hashes and create tasks
        for hash_value in get_hash_from_file(temp_file):
            logger.info(f"master got hash: {hash_value}")
            tasks[len(tasks)] = HashTask(hash_value=hash_value)

        # clean up
        temp_file.unlink()

        logger.debug(f"master processed {len(tasks)} hashes")
        return {"status": "success", "message": f"Processed {len(tasks)} hashes"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/get-task")
async def get_task(minion_id: str):
    """Get a task for a minion to process."""
    if minion_id not in minions:
        raise HTTPException(status_code=404, detail="Minion not registered")

    # Find an unassigned task
    for hash_value, task in tasks.items():
        if task.status == "pending":
            task.status = "in_progress"
            task.assigned_to = minion_id
            return {"hash": hash_value}

    return {"status": "no_tasks"}


@app.post("/submit-result")
async def submit_result(minion_id: str, hash_value: str, result: str):
    """Submit a result from a minion."""
    if minion_id not in minions:
        raise HTTPException(status_code=404, detail="Minion not registered")

    if hash_value not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task = tasks[hash_value]
    if task.assigned_to != minion_id:
        raise HTTPException(
            status_code=403, detail="Task not assigned to this minion")

    task.status = "completed"
    task.result = result
    return {"status": "success"}


@app.get("/status")
async def get_status():
    """Get the current status of all tasks and minions."""
    return {
        "minions": minions,
        "tasks": {k: v.dict() for k, v in tasks.items()}
    }

if __name__ == "__main__":
    uvicorn.run(app, host=args.host,
                log_level=args.log_level, port=MASTER_SERVER_PORT)
